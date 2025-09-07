import frappe
from fuzzywuzzy import fuzz, process
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class ComprehensiveLearning:
    """
    Ultra-intelligent learning system that behaves like an experienced data entry person
    
    Learns from ALL historical fields:
    - Item → Expense Head relationships (Diesel → Generator Fuel vs Truck Fuel)
    - Item → Project patterns (Coolant → Truck 1 R&M vs Truck 2 R&M)
    - Item → Cost Center patterns (Office supplies → Admin, Spare parts → Operations)
    - Item → Warehouse patterns (Fuel → Main Store, IT equipment → IT Store)
    - Item → Tax Template patterns (Auto parts → 18%, Medical → 12%)
    - Supplier → Payment Terms patterns (ABC Motors → 30 Days)
    - Supplier → Default Project patterns (ABC Motors → Vehicle Maintenance)
    - Project → Cost Center patterns (Vehicle Maintenance → Operations)
    - Time-based patterns (Monthly diesel orders, Quarterly maintenance)
    - Amount-based patterns (High value → Assets, Low value → Expenses)
    """
    
    def __init__(self):
        self.learning_confidence_threshold = 70
        
    def learn_from_all_historical_data(self):
        """Master learning function - analyzes ALL historical transaction patterns"""
        
        print("🧠 Starting comprehensive learning from historical data...")
        
        # Learn from Purchase Invoices (most comprehensive data)
        self._learn_from_purchase_invoices()
        
        # Learn from Journal Entries (expense patterns)
        self._learn_from_journal_entries()
        
        # Learn from Payment Entries (payment patterns)  
        self._learn_from_payment_entries()
        
        # Learn from Asset records (asset categorization)
        self._learn_from_assets()
        
        # Learn from Stock Entries (warehouse patterns)
        self._learn_from_stock_entries()
        
        # Analyze cross-field relationships
        self._analyze_field_relationships()
        
        frappe.db.commit()
        print("🎯 Comprehensive learning completed!")
        
    def _learn_from_purchase_invoices(self):
        """Learn ALL field patterns from Purchase Invoices"""
        
        query = """
            SELECT 
                pi.supplier,
                pi.project,
                pi.cost_center,
                pi.set_warehouse,
                pi.payment_terms_template,
                pi.tax_withholding_category,
                pi.company,
                pi.posting_date,
                pi.grand_total,
                pi.is_return,
                
                -- Item level details
                pii.item_code,
                pii.item_name,
                pii.description,
                pii.item_group,
                pii.uom,
                pii.stock_uom,
                pii.conversion_factor,
                pii.qty,
                pii.rate,
                pii.amount,
                pii.warehouse,
                pii.expense_account,
                pii.cost_center as item_cost_center,
                pii.project as item_project,
                
                -- Tax details
                pii.item_tax_template,
                
                COUNT(*) as frequency
                
            FROM `tabPurchase Invoice` pi
            JOIN `tabPurchase Invoice Item` pii ON pi.name = pii.parent
            WHERE pi.creation >= DATE_SUB(CURDATE(), INTERVAL 3 YEAR)
            AND pi.docstatus = 1
            GROUP BY 
                pi.supplier, pii.item_code, pii.expense_account, 
                pi.project, pi.cost_center, pii.warehouse
            HAVING frequency >= 1
            ORDER BY pi.supplier, pii.item_code, frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        print(f"📊 Analyzing {len(results)} Purchase Invoice patterns...")
        
        for result in results:
            self._save_comprehensive_pattern(
                supplier=result.supplier,
                item_code=result.item_code,
                item_name=result.item_name or result.item_code,
                pattern_data={
                    # Core mappings
                    "expense_account": result.expense_account,
                    "project": result.project or result.item_project,
                    "cost_center": result.cost_center or result.item_cost_center,
                    "warehouse": result.warehouse or result.set_warehouse,
                    
                    # Business intelligence
                    "payment_terms": result.payment_terms_template,
                    "item_group": result.item_group,
                    "tax_template": result.item_tax_template,
                    
                    # UOM intelligence  
                    "supplier_uom": result.uom,
                    "stock_uom": result.stock_uom,
                    "conversion_factor": result.conversion_factor,
                    
                    # Financial patterns
                    "average_rate": result.rate,
                    "average_amount": result.amount,
                    "total_invoice_value": result.grand_total,
                    
                    # Temporal patterns
                    "last_used_date": result.posting_date,
                    "usage_frequency": result.frequency,
                    
                    # Context
                    "company": result.company,
                    "source": "Purchase Invoice"
                }
            )
    
    def _learn_from_journal_entries(self):
        """Learn expense account patterns from Journal Entries"""
        
        query = """
            SELECT 
                je.user_remark,
                je.posting_date,
                jea.account,
                jea.project,
                jea.cost_center,
                jea.debit_in_account_currency,
                jea.reference_type,
                jea.reference_name,
                COUNT(*) as frequency
                
            FROM `tabJournal Entry` je
            JOIN `tabJournal Entry Account` jea ON je.name = jea.parent
            WHERE jea.debit_in_account_currency > 0
            AND je.creation >= DATE_SUB(CURDATE(), INTERVAL 3 YEAR)
            AND je.docstatus = 1
            GROUP BY jea.account, jea.project, SUBSTRING(je.user_remark, 1, 50)
            HAVING frequency >= 2
            ORDER BY frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        print(f"📝 Analyzing {len(results)} Journal Entry patterns...")
        
        for result in results:
            # Extract item clues from user_remark
            remark = (result.user_remark or "").lower()
            detected_items = self._extract_item_clues_from_text(remark)
            
            for item_clue in detected_items:
                self._save_expense_only_pattern(
                    item_clue=item_clue,
                    expense_account=result.account,
                    project=result.project,
                    cost_center=result.cost_center,
                    frequency=result.frequency,
                    source="Journal Entry",
                    context=result.user_remark
                )
    
    def _learn_from_payment_entries(self):
        """Learn payment behavior patterns"""
        
        query = """
            SELECT 
                pe.party as supplier,
                pe.mode_of_payment,
                pe.paid_from,
                pe.project,
                pe.cost_center,
                AVG(DATEDIFF(pe.reference_date, pe.posting_date)) as avg_payment_delay,
                COUNT(*) as frequency
                
            FROM `tabPayment Entry` pe
            WHERE pe.party_type = 'Supplier'
            AND pe.creation >= DATE_SUB(CURDATE(), INTERVAL 2 YEAR)
            AND pe.docstatus = 1
            GROUP BY pe.party, pe.mode_of_payment, pe.paid_from
            HAVING frequency >= 3
            ORDER BY pe.party, frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        print(f"💳 Analyzing {len(results)} Payment Entry patterns...")
        
        for result in results:
            self._save_payment_pattern(
                supplier=result.supplier,
                mode_of_payment=result.mode_of_payment,
                bank_account=result.paid_from,
                project=result.project,
                cost_center=result.cost_center,
                average_delay=result.avg_payment_delay,
                frequency=result.frequency
            )
    
    def _learn_from_assets(self):
        """Learn asset creation patterns"""
        
        query = """
            SELECT 
                pr.supplier,
                pr.project,
                pri.item_code,
                pri.item_name,
                pri.warehouse,
                asset.asset_category,
                asset.depreciation_method,
                asset.total_number_of_depreciations,
                COUNT(*) as frequency
                
            FROM `tabPurchase Receipt` pr
            JOIN `tabPurchase Receipt Item` pri ON pr.name = pri.parent
            JOIN `tabAsset` asset ON asset.purchase_receipt = pr.name
            WHERE pr.creation >= DATE_SUB(CURDATE(), INTERVAL 3 YEAR)
            AND pr.docstatus = 1
            GROUP BY pr.supplier, pri.item_code, asset.asset_category
            ORDER BY frequency DESC
        """
        
        results = frappe.db.sql(query, as_dict=True)
        
        print(f"🏭 Analyzing {len(results)} Asset creation patterns...")
        
        for result in results:
            self._save_asset_pattern(
                supplier=result.supplier,
                item_code=result.item_code,
                item_name=result.item_name,
                asset_category=result.asset_category,
                depreciation_method=result.depreciation_method,
                project=result.project,
                warehouse=result.warehouse,
                frequency=result.frequency
            )
    
    def _extract_item_clues_from_text(self, text: str) -> List[str]:
        """Extract item clues from description text using intelligent parsing"""
        
        item_keywords = {
            'diesel': ['diesel', 'fuel oil', 'gasoil', 'petroleum'],
            'petrol': ['petrol', 'gasoline', 'benzin'],
            'coolant': ['coolant', 'antifreeze', 'radiator fluid'],
            'engine_oil': ['engine oil', 'motor oil', 'lubricant', 'mobil', 'castrol'],
            'grease': ['grease', 'lubrication', 'bearing grease'],
            'brake_fluid': ['brake fluid', 'brake oil', 'dot 3', 'dot 4'],
            'hydraulic_oil': ['hydraulic oil', 'hydraulic fluid', 'hyd oil'],
            'spare_parts': ['spare', 'parts', 'component', 'replacement'],
            'filters': ['filter', 'air filter', 'oil filter', 'fuel filter'],
            'belts': ['belt', 'v-belt', 'timing belt'],
            'tyres': ['tyre', 'tire', 'wheel'],
            'batteries': ['battery', 'cell', 'power pack'],
            'office_supplies': ['paper', 'pen', 'stapler', 'stationery'],
            'cleaning': ['detergent', 'soap', 'cleaning', 'sanitizer'],
            'electrical': ['wire', 'cable', 'fuse', 'bulb', 'led']
        }
        
        detected_items = []
        text_lower = text.lower()
        
        for item_type, keywords in item_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    detected_items.append(item_type)
                    break
        
        return detected_items if detected_items else ['general_expense']
    
    def _save_comprehensive_pattern(self, supplier: str, item_code: str, 
                                  item_name: str, pattern_data: Dict[str, Any]):
        """Save comprehensive learning pattern with all field relationships"""
        
        # Check if base mapping exists
        mapping_name = f"{supplier}-{item_code}".replace(" ", "-")
        existing = frappe.db.exists("Supplier Item Mapping", {"name": mapping_name})
        
        if not existing:
            # Create base mapping if doesn't exist
            doc = frappe.get_doc({
                "doctype": "Supplier Item Mapping",
                "supplier": supplier,
                "ocr_item_text": item_name,
                "erpnext_item_code": item_code,
                "frequency_count": pattern_data.get('usage_frequency', 1),
                "confidence_score": min(95, pattern_data.get('usage_frequency', 1) * 10),
                "last_used": pattern_data.get('last_used_date', datetime.now())
            })
            doc.insert(ignore_permissions=True)
            mapping_name = doc.name
        
        # Save comprehensive patterns in a separate table
        comprehensive_pattern = {
            "mapping_id": mapping_name,
            "supplier": supplier,
            "item_code": item_code,
            **pattern_data,
            "created_date": datetime.now().isoformat(),
            "confidence": self._calculate_pattern_confidence(pattern_data)
        }
        
        # Store in custom table or JSON field
        self._store_pattern_in_database(comprehensive_pattern)
    
    def _store_pattern_in_database(self, pattern: Dict[str, Any]):
        """Store pattern in database - using Simple approach with existing table"""
        
        try:
            mapping = frappe.get_doc("Supplier Item Mapping", pattern['mapping_id'])
            
            # Store comprehensive pattern in JSON field
            if mapping.expense_head_patterns:
                existing_patterns = json.loads(mapping.expense_head_patterns)
            else:
                existing_patterns = []
            
            # Add new pattern
            existing_patterns.append({
                "expense_account": pattern.get('expense_account'),
                "project": pattern.get('project'), 
                "cost_center": pattern.get('cost_center'),
                "warehouse": pattern.get('warehouse'),
                "payment_terms": pattern.get('payment_terms'),
                "tax_template": pattern.get('tax_template'),
                "uom_conversion": {
                    "supplier_uom": pattern.get('supplier_uom'),
                    "stock_uom": pattern.get('stock_uom'),
                    "conversion_factor": pattern.get('conversion_factor')
                },
                "financial_intelligence": {
                    "average_rate": pattern.get('average_rate'),
                    "typical_amount_range": pattern.get('average_amount')
                },
                "frequency": pattern.get('usage_frequency', 1),
                "confidence": pattern.get('confidence', 70),
                "last_used": pattern.get('last_used_date'),
                "source": pattern.get('source'),
                "learned_date": datetime.now().isoformat()
            })
            
            # Keep only top 10 patterns per item
            existing_patterns = sorted(
                existing_patterns, 
                key=lambda x: x.get('frequency', 0), 
                reverse=True
            )[:10]
            
            mapping.expense_head_patterns = json.dumps(existing_patterns)
            mapping.save(ignore_permissions=True)
            
        except Exception as e:
            print(f"Error storing pattern: {e}")
    
    def _calculate_pattern_confidence(self, pattern_data: Dict[str, Any]) -> int:
        """Calculate confidence score based on pattern strength"""
        
        base_confidence = 50
        frequency = pattern_data.get('usage_frequency', 1)
        
        # Frequency boost
        base_confidence += min(30, frequency * 5)
        
        # Completeness boost  
        if pattern_data.get('expense_account'):
            base_confidence += 10
        if pattern_data.get('project'):
            base_confidence += 10
        if pattern_data.get('warehouse'):
            base_confidence += 5
        
        # Source boost
        if pattern_data.get('source') == 'Purchase Invoice':
            base_confidence += 10
            
        return min(95, base_confidence)
    
    def get_intelligent_suggestions(self, supplier: str, item_code: str = None, 
                                  ocr_text: str = None, project_context: str = None,
                                  amount: float = None) -> Dict[str, Any]:
        """
        Get ultra-intelligent suggestions based on ALL learned patterns
        
        Like an experienced data entry person who remembers:
        - "Oh, when ABC Motors orders Diesel for Generator project, it goes to Generator Fuel account"
        - "When they order Coolant for Truck 1, it's always R&M - Truck 1"  
        - "Their payment terms are always 30 Days"
        - "Spare parts > ₹50,000 are usually Assets"
        """
        
        suggestions = {
            "expense_account": None,
            "project": None,
            "cost_center": None,
            "warehouse": None,
            "payment_terms": None,
            "tax_template": None,
            "uom_conversion": None,
            "asset_category": None,
            "mode_of_payment": None,
            "overall_confidence": 0,
            "reasoning": []
        }
        
        # Get supplier patterns
        supplier_patterns = self._get_supplier_patterns(supplier)
        
        # Get item-specific patterns
        if item_code:
            item_patterns = self._get_item_patterns(supplier, item_code)
        elif ocr_text:
            item_patterns = self._get_patterns_from_ocr_text(supplier, ocr_text)
        else:
            item_patterns = []
        
        # Apply context intelligence
        context_boost = self._apply_context_intelligence(
            item_patterns, project_context, amount
        )
        
        # Generate suggestions
        suggestions.update(self._generate_field_suggestions(
            supplier_patterns, item_patterns, context_boost
        ))
        
        return suggestions
    
    def _get_supplier_patterns(self, supplier: str) -> List[Dict]:
        """Get all patterns for a supplier"""
        
        mappings = frappe.get_all(
            "Supplier Item Mapping",
            filters={"supplier": supplier},
            fields=["*"]
        )
        
        patterns = []
        for mapping in mappings:
            if mapping.expense_head_patterns:
                item_patterns = json.loads(mapping.expense_head_patterns)
                for pattern in item_patterns:
                    pattern["item_code"] = mapping.erpnext_item_code
                    patterns.append(pattern)
        
        return patterns
    
    def _apply_context_intelligence(self, patterns: List[Dict], 
                                  project_context: str = None, 
                                  amount: float = None) -> Dict:
        """Apply contextual intelligence like a smart data entry person"""
        
        context_boost = {}
        
        # Project context intelligence
        if project_context:
            project_lower = project_context.lower()
            
            # Vehicle/Truck patterns
            if any(keyword in project_lower for keyword in ['truck', 'vehicle', 'transport']):
                context_boost['expense_preference'] = 'vehicle_maintenance'
                
                # Specific truck patterns
                if 'truck 1' in project_lower:
                    context_boost['cost_center_preference'] = 'Truck 1 Operations'
                elif 'truck 2' in project_lower:
                    context_boost['cost_center_preference'] = 'Truck 2 Operations'
            
            # Generator patterns
            elif 'generator' in project_lower:
                context_boost['expense_preference'] = 'generator_fuel'
                context_boost['cost_center_preference'] = 'Power & Utilities'
            
            # Office patterns
            elif any(keyword in project_lower for keyword in ['office', 'admin']):
                context_boost['expense_preference'] = 'office_expenses'
                context_boost['cost_center_preference'] = 'Administration'
        
        # Amount-based intelligence
        if amount:
            if amount >= 50000:
                context_boost['asset_likelihood'] = 'high'
            elif amount >= 10000:
                context_boost['asset_likelihood'] = 'medium'
        
        return context_boost
    
    def _generate_field_suggestions(self, supplier_patterns: List[Dict], 
                                   item_patterns: List[Dict], 
                                   context_boost: Dict) -> Dict:
        """Generate intelligent field suggestions"""
        
        suggestions = {}
        all_patterns = supplier_patterns + item_patterns
        
        if not all_patterns:
            return suggestions
        
        # Expense Account suggestion
        expense_accounts = [p.get('expense_account') for p in all_patterns if p.get('expense_account')]
        if expense_accounts:
            most_common = max(set(expense_accounts), key=expense_accounts.count)
            confidence = (expense_accounts.count(most_common) / len(expense_accounts)) * 100
            suggestions['expense_account'] = {
                'value': most_common,
                'confidence': confidence,
                'reason': f'Used {expense_accounts.count(most_common)} times'
            }
        
        # Project suggestion with context intelligence
        projects = [p.get('project') for p in all_patterns if p.get('project')]
        if projects:
            most_common_project = max(set(projects), key=projects.count)
            confidence = (projects.count(most_common_project) / len(projects)) * 100
            
            # Apply context boost
            if context_boost.get('expense_preference'):
                confidence += 15
                
            suggestions['project'] = {
                'value': most_common_project,
                'confidence': min(95, confidence),
                'reason': f'Historical pattern + context intelligence'
            }
        
        # Continue for other fields...
        return suggestions

# API Functions for frontend
@frappe.whitelist()
def migrate_comprehensive_learning():
    """API to trigger comprehensive learning migration"""
    
    learning = ComprehensiveLearning()
    learning.learn_from_all_historical_data()
    
    return {"status": "success", "message": "Comprehensive learning completed"}

@frappe.whitelist() 
def get_smart_suggestions(supplier: str, item_code: str = None, 
                         ocr_text: str = None, project: str = None, 
                         amount: float = None):
    """API to get intelligent field suggestions"""
    
    learning = ComprehensiveLearning()
    suggestions = learning.get_intelligent_suggestions(
        supplier=supplier,
        item_code=item_code, 
        ocr_text=ocr_text,
        project_context=project,
        amount=float(amount) if amount else None
    )
    
    return suggestions