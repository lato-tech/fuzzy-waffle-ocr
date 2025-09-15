import frappe
from frappe.model.document import Document
import json

class SupplierItemMapping(Document):
    def validate(self):
        self.update_success_rate()
        
    def update_success_rate(self):
        """Calculate success rate based on corrections"""
        if self.user_correction_count and self.frequency_count:
            success_count = self.frequency_count - self.user_correction_count
            self.success_rate = (success_count / self.frequency_count) * 100
        else:
            self.success_rate = 100 if self.frequency_count > 0 else 0
    
    def add_expense_head_pattern(self, expense_head: str, project: str = None, cost_center: str = None):
        """Add expense head learning pattern"""
        expense_pattern = {
            "expense_head": expense_head,
            "project": project,
            "cost_center": cost_center,
            "frequency": 1
        }
        
        # Get existing patterns
        if self.expense_head_patterns:
            patterns = json.loads(self.expense_head_patterns)
        else:
            patterns = []
        
        # Check if pattern exists
        existing_pattern = None
        for pattern in patterns:
            if (pattern.get('expense_head') == expense_head and 
                pattern.get('project') == project):
                existing_pattern = pattern
                break
        
        if existing_pattern:
            existing_pattern['frequency'] += 1
        else:
            patterns.append(expense_pattern)
        
        self.expense_head_patterns = json.dumps(patterns)
        
    def get_suggested_expense_head(self, project: str = None) -> dict:
        """Get suggested expense head based on learning patterns"""
        if not self.expense_head_patterns:
            return None
            
        patterns = json.loads(self.expense_head_patterns)
        
        if project:
            # Filter by project first
            project_patterns = [p for p in patterns if p.get('project') == project]
            if project_patterns:
                # Return most frequent for this project
                best_pattern = max(project_patterns, key=lambda x: x.get('frequency', 0))
                return {
                    "expense_head": best_pattern['expense_head'],
                    "project": best_pattern.get('project'),
                    "cost_center": best_pattern.get('cost_center'),
                    "confidence": min(95, best_pattern['frequency'] * 10)
                }
        
        # Return overall most frequent
        if patterns:
            best_pattern = max(patterns, key=lambda x: x.get('frequency', 0))
            return {
                "expense_head": best_pattern['expense_head'],
                "project": best_pattern.get('project'),
                "cost_center": best_pattern.get('cost_center'),
                "confidence": min(85, best_pattern['frequency'] * 8)
            }