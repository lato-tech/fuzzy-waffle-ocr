import frappe
from frappe.model.document import Document

class OCRSettings(Document):
    def validate(self):
        """Validate OCR settings"""
        
        if self.ai_enabled and not self.openai_api_key:
            frappe.throw("OpenAI API Key is required when AI Enhancement is enabled")
        
        if self.google_vision_enabled and not self.google_vision_credentials:
            frappe.throw("Google Vision credentials JSON file is required when Google Vision API is enabled")
        
        if self.confidence_threshold > self.auto_submit_threshold:
            frappe.throw("Auto Submit Threshold must be higher than Confidence Threshold")
    
    def on_update(self):
        """Clear cache when settings are updated"""
        frappe.clear_cache()
        
        # Test API connections if enabled
        if self.ai_enabled and self.openai_api_key:
            self.test_openai_connection()
    
    def test_openai_connection(self):
        """Test OpenAI API connection"""
        try:
            import openai
            openai.api_key = self.openai_api_key
            
            # Simple test call
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=5
            )
            
            frappe.msgprint("✅ OpenAI API connection successful!", alert=True)
            
        except Exception as e:
            frappe.throw(f"❌ OpenAI API connection failed: {e}")
    
    def get_ai_config(self):
        """Get AI configuration for processors"""
        return {
            "enabled": self.ai_enabled,
            "api_key": self.openai_api_key if self.ai_enabled else None,
            "model": self.ai_model,
            "max_tokens": self.max_tokens,
            "confidence_threshold": self.ai_confidence_threshold
        }