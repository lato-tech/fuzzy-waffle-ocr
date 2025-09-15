import frappe
from fuzzywuzzy import fuzz, process
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

class ExpenseHeadLearning:
    """
    Advanced expense head learning system that understands:
    - Item-specific expense patterns (Diesel → Generator Fuel vs Truck Fuel)  
    - Project-specific usage (Coolant for Truck 1 vs Truck 2)
    - Context-aware suggestions based on historical data
    """
    
    def __init__(self, supplier: str = None):
        self.supplier = supplier
        
    def learn_from_historical_data(self):
        """Learn expense head patterns from historical Purchase Invoices and Journal Entries"""
        
        # Learn from Purchase Invoices
        self._learn_from_purchase_invoices()
        
        # Learn from Journal Entries  
        self._learn_from_journal_entries()
        
        frappe.db.commit()
        
    def _learn_from_purchase_invoices(self):
        """Extract patterns from Purchase Invoice items"""
        
        # Get Purchase Invoices with expense head data
        query = """
            SELECT 
                pi.supplier,
                pi.project,
                pi.cost_center,
                pii.item_code,
                pii.item_name,
                pii.expense_account,
                COUNT(*) as frequency,
                pi.creation
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            WHERE pii.expense_account IS NOT NULL 
            AND pii.expense_account != ''
            AND pi.creation >= DATE_SUB(CURDATE(), INTERVAL 3 YEAR)
            GROUP BY pi.supplier, pii.item_code, pii.expense_account, pi.project
            ORDER BY frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        for result in results:
            self._save_expense_pattern(
                supplier=result.supplier,
                item_code=result.item_code,
                item_name=result.item_name,
                expense_head=result.expense_account,
                project=result.project,
                cost_center=result.cost_center,
                frequency=result.frequency,
                source="Purchase Invoice"
            )
    
    def _learn_from_journal_entries(self):
        """Extract patterns from Journal Entry accounts"""
        
        query = """
            SELECT 
                je.user_remark,
                jea.account,
                jea.project,
                jea.cost_center,
                jea.debit_in_account_currency,
                COUNT(*) as frequency
            FROM `tabJournal Entry` je
            JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
            WHERE jea.debit_in_account_currency > 0
            AND je.creation >= DATE_SUB(CURDATE(), INTERVAL 3 YEAR)
            AND je.user_remark IS NOT NULL
            GROUP BY jea.account, jea.project, je.user_remark
            HAVING frequency >= 2
            ORDER BY frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        for result in results:
            # Extract item hints from user_remark
            remark = result.user_remark.lower()
            
            # Common patterns
            item_patterns = {
                'diesel': ['diesel', 'fuel', 'petrol'],
                'coolant': ['coolant', 'radiator'],
                'oil': ['oil', 'lubricant', 'grease'],
                'parts': ['spare', 'parts', 'component']
            }
            
            detected_item = None
            for item_type, keywords in item_patterns.items():
                if any(keyword in remark for keyword in keywords):
                    detected_item = item_type
                    break
            
            if detected_item:
                self._save_expense_pattern(
                    supplier="Journal Entry",
                    item_code=detected_item,
                    item_name=detected_item.title(),
                    expense_head=result.account,
                    project=result.project,
                    cost_center=result.cost_center,
                    frequency=result.frequency,
                    source="Journal Entry"
                )
    
    def _save_expense_pattern(self, supplier: str, item_code: str, item_name: str, 
                            expense_head: str, project: str = None, cost_center: str = None,
                            frequency: int = 1, source: str = "Manual"):
        """Save learned expense head pattern"""
        
        # Check if mapping exists
        existing = frappe.db.exists(
            "Supplier Item Mapping",
            {
                "supplier": supplier,
                "erpnext_item_code": item_code
            }
        )
        
        expense_pattern = {
            "expense_head": expense_head,
            "project": project,
            "cost_center": cost_center,
            "frequency": frequency,
            "source": source,
            "learned_date": datetime.now().isoformat()
        }
        
        if existing:
            # Update existing mapping
            doc = frappe.get_doc("Supplier Item Mapping", existing)
            
            # Add to expense patterns
            if doc.expense_head_patterns:
                patterns = json.loads(doc.expense_head_patterns)
            else:
                patterns = []
            
            # Check if this exact pattern exists
            existing_pattern = None
            for pattern in patterns:
                if (pattern.get('expense_head') == expense_head and
                    pattern.get('project') == project):
                    existing_pattern = pattern
                    break
            
            if existing_pattern:
                existing_pattern['frequency'] += frequency
            else:
                patterns.append(expense_pattern)
            
            doc.expense_head_patterns = json.dumps(patterns)
            
            # Set default if this is most frequent
            if not doc.default_expense_head or frequency > 5:
                doc.default_expense_head = expense_head
                
            doc.save(ignore_permissions=True)
            
        else:
            # Create new mapping
            doc = frappe.get_doc({
                "doctype": "Supplier Item Mapping",
                "supplier": supplier,
                "ocr_item_text": item_name,
                "erpnext_item_code": item_code,
                "frequency_count": frequency,
                "confidence_score": 75,  # Medium confidence for historical data
                "expense_head_patterns": json.dumps([expense_pattern]),
                "default_expense_head": expense_head,
                "last_used": datetime.now()
            })
            doc.insert(ignore_permissions=True)
    
    def suggest_expense_head(self, item_code: str, supplier: str = None, 
                           project: str = None) -> Dict[str, Any]:
        """
        Suggest expense head for item based on learned patterns
        
        Examples:
        - Diesel + Project "Generator" → "Generator Fuel Expenses"
        - Diesel + Project "Truck 1" → "Vehicle Fuel - Truck 1" 
        - Coolant + Project "Truck 2" → "Repairs & Maintenance - Truck 2"
        """
        
        filters = {"erpnext_item_code": item_code}
        if supplier:
            filters["supplier"] = supplier
            
        mappings = frappe.get_all(
            "Supplier Item Mapping",
            filters=filters,
            fields=["*"]
        )
        
        if not mappings:
            return self._get_default_expense_head(item_code)
        
        best_suggestion = None
        highest_confidence = 0
        
        for mapping in mappings:
            if not mapping.expense_head_patterns:
                continue
                
            patterns = json.loads(mapping.expense_head_patterns)
            
            for pattern in patterns:
                confidence = self._calculate_pattern_confidence(pattern, project)
                
                if confidence > highest_confidence:
                    highest_confidence = confidence
                    best_suggestion = {
                        "expense_head": pattern['expense_head'],
                        "project": pattern.get('project'),
                        "cost_center": pattern.get('cost_center'),
                        "confidence": confidence,
                        "reason": self._get_suggestion_reason(pattern, project)
                    }
        
        return best_suggestion if best_suggestion else self._get_default_expense_head(item_code)
    
    def _calculate_pattern_confidence(self, pattern: Dict, current_project: str = None) -> int:
        """Calculate confidence score for expense head pattern"""
        
        base_confidence = min(90, pattern.get('frequency', 1) * 15)
        
        # Boost confidence for exact project match
        if current_project and pattern.get('project') == current_project:
            base_confidence += 20
        
        # Reduce confidence for generic patterns
        if not pattern.get('project'):
            base_confidence -= 10
            
        return min(95, max(30, base_confidence))
    
    def _get_suggestion_reason(self, pattern: Dict, current_project: str = None) -> str:
        """Generate human-readable reason for suggestion"""
        
        frequency = pattern.get('frequency', 1)
        project = pattern.get('project')
        
        if current_project and project == current_project:
            return f"Used {frequency} times for project '{project}'"
        elif project:
            return f"Used {frequency} times (mostly for project '{project}')"
        else:
            return f"Used {frequency} times historically"
    
    def _get_default_expense_head(self, item_code: str) -> Dict[str, Any]:
        """Get default expense head based on item category"""
        
        item = frappe.get_doc("Item", item_code)
        item_group = item.item_group.lower() if item.item_group else ""
        
        # Default mappings based on item group
        default_mappings = {
            'fuel': 'Fuel Expenses - Company',
            'oil': 'Repairs and Maintenance - Company', 
            'spare parts': 'Repairs and Maintenance - Company',
            'consumables': 'Consumables - Company',
            'office supplies': 'Office Maintenance Expenses - Company',
            'stationery': 'Office Maintenance Expenses - Company'
        }
        
        for keyword, expense_head in default_mappings.items():
            if keyword in item_group or keyword in item.item_name.lower():
                return {
                    "expense_head": expense_head,
                    "project": None,
                    "cost_center": None,
                    "confidence": 60,
                    "reason": f"Default for {keyword} items"
                }
        
        return {
            "expense_head": "General Expenses - Company",
            "confidence": 40,
            "reason": "Generic default"
        }
    
    def get_expense_analytics(self, supplier: str = None) -> Dict[str, Any]:
        """Get analytics on expense head learning patterns"""
        
        filters = {}
        if supplier:
            filters["supplier"] = supplier
            
        mappings = frappe.get_all(
            "Supplier Item Mapping",
            filters=filters,
            fields=["*"]
        )
        
        analytics = {
            "total_items": len(mappings),
            "items_with_expense_learning": 0,
            "expense_head_distribution": {},
            "project_distribution": {},
            "learning_sources": {"Purchase Invoice": 0, "Journal Entry": 0, "Manual": 0}
        }
        
        for mapping in mappings:
            if mapping.expense_head_patterns:
                analytics["items_with_expense_learning"] += 1
                
                patterns = json.loads(mapping.expense_head_patterns)
                for pattern in patterns:
                    # Expense head distribution
                    expense_head = pattern.get('expense_head', 'Unknown')
                    analytics["expense_head_distribution"][expense_head] = \
                        analytics["expense_head_distribution"].get(expense_head, 0) + pattern.get('frequency', 1)
                    
                    # Project distribution
                    project = pattern.get('project', 'No Project')
                    analytics["project_distribution"][project] = \
                        analytics["project_distribution"].get(project, 0) + pattern.get('frequency', 1)
                    
                    # Source tracking
                    source = pattern.get('source', 'Manual')
                    analytics["learning_sources"][source] = \
                        analytics["learning_sources"].get(source, 0) + 1
        
        return analytics

@frappe.whitelist()
def migrate_expense_head_patterns():
    """Migrate expense head patterns from historical data"""
    
    learning = ExpenseHeadLearning()
    learning.learn_from_historical_data()
    
    return "Expense head patterns migrated successfully"

@frappe.whitelist()
def get_item_expense_suggestions(item_code: str, supplier: str = None, project: str = None):
    """API endpoint to get expense head suggestions"""
    
    learning = ExpenseHeadLearning()
    suggestion = learning.suggest_expense_head(item_code, supplier, project)
    
    return suggestion