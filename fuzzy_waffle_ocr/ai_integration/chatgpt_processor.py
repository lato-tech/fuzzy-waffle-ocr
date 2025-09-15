import frappe
import openai
import json
from typing import Dict, List, Any, Optional
import requests

class ChatGPTInvoiceProcessor:
    """
    Phase 2: ChatGPT AI Integration for Enhanced Invoice Processing
    
    This module integrates ChatGPT API to provide:
    1. Advanced handwritten text interpretation
    2. Contextual data extraction from poor quality images
    3. Intelligent data validation and correction suggestions
    4. Natural language processing for expense categorization
    5. Advanced UOM conversion with context understanding
    """
    
    def __init__(self):
        self.settings = self.get_ai_settings()
        if self.settings.get('openai_api_key'):
            openai.api_key = self.settings['openai_api_key']
    
    def get_ai_settings(self) -> Dict[str, Any]:
        """Get AI integration settings"""
        try:
            settings = frappe.get_single("OCR Settings")
            return {
                "openai_api_key": settings.get("openai_api_key"),
                "ai_enabled": settings.get("ai_enabled", False),
                "ai_model": settings.get("ai_model", "gpt-4"),
                "max_tokens": settings.get("max_tokens", 2000)
            }
        except:
            return {
                "ai_enabled": False,
                "ai_model": "gpt-3.5-turbo",
                "max_tokens": 1500
            }
    
    def enhance_ocr_with_ai(self, raw_ocr_text: str, image_context: Dict = None) -> Dict[str, Any]:
        """
        Use ChatGPT to enhance and interpret OCR results
        
        Especially useful for:
        - Handwritten bills with unclear text
        - Poor quality images
        - Contextual interpretation of abbreviations
        - Smart correction of OCR errors
        """
        
        if not self.settings.get('ai_enabled') or not self.settings.get('openai_api_key'):
            return {"enhanced_text": raw_ocr_text, "ai_used": False}
        
        prompt = self._build_ocr_enhancement_prompt(raw_ocr_text, image_context)
        
        try:
            response = openai.ChatCompletion.create(
                model=self.settings['ai_model'],
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert invoice data extraction assistant. You specialize in interpreting OCR results from invoices, especially handwritten ones, and extracting structured data."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                max_tokens=self.settings['max_tokens'],
                temperature=0.1  # Low temperature for consistent results
            )
            
            ai_result = json.loads(response.choices[0].message.content)
            ai_result["ai_used"] = True
            ai_result["ai_confidence"] = self._calculate_ai_confidence(ai_result)
            
            return ai_result
            
        except Exception as e:
            frappe.log_error(f"ChatGPT API Error: {e}", "AI Invoice Processing")
            return {"enhanced_text": raw_ocr_text, "ai_used": False, "error": str(e)}
    
    def _build_ocr_enhancement_prompt(self, raw_text: str, context: Dict = None) -> str:
        """Build comprehensive prompt for ChatGPT OCR enhancement"""
        
        prompt = f"""
I need you to analyze this OCR text from an invoice and extract structured information. The OCR might have errors, especially from handwritten text.

RAW OCR TEXT:
{raw_text}

Please extract and return a JSON response with the following structure:

{{
    "enhanced_text": "cleaned and corrected version of the OCR text",
    "invoice_data": {{
        "invoice_number": "extracted invoice/bill number",
        "date": "extracted date in YYYY-MM-DD format",
        "supplier_name": "extracted supplier/vendor name", 
        "total_amount": "total amount as number",
        "items": [
            {{
                "description": "item description",
                "quantity": "quantity as number",
                "unit": "unit of measurement (standardize to common units)",
                "rate": "rate per unit as number",
                "amount": "line total as number"
            }}
        ]
    }},
    "suggestions": {{
        "expense_categories": ["suggested expense account heads"],
        "uom_conversions": [
            {{
                "original": "original unit from OCR",
                "suggested": "standardized unit",
                "conversion_factor": "multiplication factor",
                "reasoning": "why this conversion makes sense"
            }}
        ],
        "data_quality": {{
            "confidence": "high/medium/low - your confidence in the extraction",
            "issues": ["list any unclear or problematic parts"],
            "improvements": ["suggestions for better OCR results"]
        }}
    }}
}}

CONTEXT HINTS:
- This is likely a business invoice/bill
- Common Indian currency (₹) and units (Kg, Lt, Pcs, Nos)
- Look for patterns like item descriptions followed by quantities and amounts
- Handwritten text might have OCR errors - use context to correct them
- Standardize units (e.g., "Kgs" -> "Kg", "Ltr" -> "Lt", "Pieces" -> "Pcs")

Please be thorough and use business context to interpret unclear text.
"""
        
        return prompt
    
    def intelligent_item_categorization(self, item_description: str, supplier_context: str = None) -> Dict[str, Any]:
        """
        Use ChatGPT for intelligent expense head categorization
        
        Examples:
        - "Diesel for generator" -> Generator Fuel Expenses
        - "Coolant for Truck 1" -> Vehicle Maintenance - Truck 1
        - "Office stationery" -> Office Expenses
        """
        
        if not self.settings.get('ai_enabled'):
            return {"category": "General Expenses", "ai_used": False}
        
        prompt = f"""
Analyze this item description and suggest the most appropriate expense account head:

Item: "{item_description}"
Supplier Context: "{supplier_context or 'Not provided'}"

Based on common business expense categories, suggest:

1. Primary expense account head
2. Alternative options
3. Project/cost center suggestions if applicable
4. Reasoning for the categorization

Return JSON format:
{{
    "primary_category": "Most likely expense account head",
    "alternatives": ["alternative categories"],
    "project_hints": ["suggested project types"],
    "cost_center_hints": ["suggested cost centers"], 
    "confidence": "high/medium/low",
    "reasoning": "explanation of categorization logic"
}}

Consider categories like:
- Fuel Expenses, Vehicle Maintenance, Office Expenses
- Repairs & Maintenance, Professional Services
- Raw Materials, Consumables, Utilities
- Equipment, IT Expenses, Travel Expenses
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500,
                temperature=0.2
            )
            
            result = json.loads(response.choices[0].message.content)
            result["ai_used"] = True
            return result
            
        except Exception as e:
            return {
                "primary_category": "General Expenses", 
                "ai_used": False,
                "error": str(e)
            }
    
    def smart_uom_conversion(self, item_text: str, quantity: float, unit: str) -> Dict[str, Any]:
        """
        Use ChatGPT for intelligent UOM conversion with business context
        
        Examples:
        - "Grease 2kg - 1 Pcs" -> Convert 1 Pcs to 2 Kg
        - "Oil 500ml bottle - 3 Nos" -> Convert 3 Nos to 1.5 Lt  
        """
        
        prompt = f"""
Analyze this item and suggest the best UOM conversion for business inventory:

Item Description: "{item_text}"
OCR Quantity: {quantity}
OCR Unit: "{unit}"

The item description might contain clues about the actual unit that should be used.
For example: "Grease 2kg - 1 Pcs" means 1 piece contains 2kg, so it should be 2 Kg.

Please suggest:
1. Whether conversion is needed
2. What the final quantity and unit should be  
3. The conversion logic
4. Rate adjustment needed

Return JSON:
{{
    "needs_conversion": true/false,
    "original": {{"quantity": {quantity}, "unit": "{unit}"}},
    "converted": {{"quantity": "final quantity", "unit": "final unit"}},
    "conversion_factor": "multiplication factor",
    "reasoning": "explanation of conversion logic",
    "rate_adjustment": "how to adjust the rate (multiply/divide by factor)"
}}
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            result["ai_used"] = True
            return result
            
        except Exception as e:
            return {
                "needs_conversion": False,
                "original": {"quantity": quantity, "unit": unit},
                "ai_used": False,
                "error": str(e)
            }
    
    def validate_extracted_data(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use ChatGPT to validate and suggest corrections for extracted invoice data
        """
        
        prompt = f"""
Review this extracted invoice data for consistency and potential errors:

{json.dumps(extracted_data, indent=2)}

Check for:
1. Mathematical consistency (quantities × rates = amounts)
2. Reasonable values for items and amounts
3. Date format and validity
4. Missing critical information
5. Unusual patterns that might indicate OCR errors

Return JSON with validation results:
{{
    "validation_status": "valid/has_warnings/has_errors",
    "math_check": {{"status": "pass/fail", "details": "math validation results"}},
    "data_quality": {{"score": "1-10", "issues": ["list of issues found"]}},
    "suggestions": ["specific suggestions for corrections"],
    "confidence": "overall confidence in the data quality"
}}
"""
        
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo", 
                messages=[{"role": "user", "content": prompt}],
                max_tokens=600,
                temperature=0.1
            )
            
            result = json.loads(response.choices[0].message.content)
            result["ai_used"] = True
            return result
            
        except Exception as e:
            return {
                "validation_status": "unknown",
                "ai_used": False,
                "error": str(e)
            }
    
    def _calculate_ai_confidence(self, ai_result: Dict) -> int:
        """Calculate confidence score based on AI response completeness"""
        
        confidence = 50  # Base confidence
        
        # Boost for complete data
        if ai_result.get('invoice_data', {}).get('invoice_number'):
            confidence += 10
        if ai_result.get('invoice_data', {}).get('total_amount'):
            confidence += 10
        if ai_result.get('invoice_data', {}).get('items'):
            confidence += 15
        if ai_result.get('invoice_data', {}).get('supplier_name'):
            confidence += 10
            
        # Boost for quality suggestions
        if ai_result.get('suggestions', {}).get('uom_conversions'):
            confidence += 5
            
        return min(95, confidence)

# API Functions
@frappe.whitelist()
def process_with_ai_enhancement(ocr_text: str, image_context: Dict = None):
    """API endpoint for AI-enhanced OCR processing"""
    
    processor = ChatGPTInvoiceProcessor()
    result = processor.enhance_ocr_with_ai(ocr_text, image_context)
    
    return result

@frappe.whitelist()
def get_ai_item_categorization(item_description: str, supplier: str = None):
    """API endpoint for AI-powered item categorization"""
    
    processor = ChatGPTInvoiceProcessor()
    result = processor.intelligent_item_categorization(item_description, supplier)
    
    return result

@frappe.whitelist()
def validate_invoice_data_with_ai(data: Dict[str, Any]):
    """API endpoint for AI validation of extracted data"""
    
    processor = ChatGPTInvoiceProcessor()
    result = processor.validate_extracted_data(data)
    
    return result