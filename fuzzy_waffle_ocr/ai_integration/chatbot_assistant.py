import frappe
import json
from typing import Dict, List, Any, Optional

class FuzzyWaffleAssistant:
    """
    Intelligent ChatBot Assistant for Fuzzy Waffle OCR
    
    Features:
    1. Help users with invoice processing questions
    2. Explain OCR results and learning patterns
    3. Suggest improvements for better accuracy
    4. Guide through expense head categorization
    5. Assist with UOM conversions and mappings
    """
    
    def __init__(self):
        self.settings = self.get_chatbot_settings()
        self.context_memory = {}
    
    def get_chatbot_settings(self) -> Dict[str, Any]:
        """Get chatbot settings, prefer Raven integration if available"""
        
        # Try to get settings from Fuzzy Waffle OCR Settings first
        try:
            ocr_settings = frappe.get_single("OCR Settings")
            if ocr_settings.get("chatbot_enabled") and ocr_settings.get("openai_api_key"):
                return {
                    "enabled": True,
                    "api_key": ocr_settings.openai_api_key,
                    "model": ocr_settings.get("ai_model", "gpt-3.5-turbo"),
                    "source": "fuzzy_waffle"
                }
        except:
            pass
        
        # Fallback to Raven settings if available
        try:
            raven_settings = frappe.get_single("Raven Settings")
            if raven_settings.get("openai_api_key"):
                return {
                    "enabled": True,
                    "api_key": raven_settings.openai_api_key,
                    "model": raven_settings.get("openai_model", "gpt-3.5-turbo"),
                    "source": "raven"
                }
        except:
            pass
        
        return {"enabled": False, "source": "none"}
    
    def chat(self, user_message: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Main chat interface for the assistant"""
        
        if not self.settings.get("enabled"):
            return {
                "response": "AI Assistant is not configured. Please set up OpenAI API key in OCR Settings.",
                "type": "error"
            }
        
        # Build system prompt with OCR context
        system_prompt = self._build_system_prompt(context)
        
        # Prepare conversation
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Add conversation history if available
        if context and context.get("conversation_id"):
            history = self._get_conversation_history(context["conversation_id"])
            messages.extend(history)
        
        try:
            # Use Raven's OpenAI integration if available
            if self.settings["source"] == "raven":
                response = self._chat_via_raven(messages)
            else:
                response = self._chat_direct_openai(messages)
            
            # Save to conversation history
            if context and context.get("conversation_id"):
                self._save_to_history(context["conversation_id"], user_message, response)
            
            return {
                "response": response,
                "type": "success",
                "source": self.settings["source"]
            }
            
        except Exception as e:
            frappe.log_error(f"Chatbot Error: {e}", "Fuzzy Waffle Assistant")
            return {
                "response": f"I'm experiencing technical difficulties: {str(e)}",
                "type": "error"
            }
    
    def _build_system_prompt(self, context: Dict[str, Any] = None) -> str:
        """Build comprehensive system prompt for OCR assistant"""
        
        base_prompt = """
You are the Fuzzy Waffle OCR Assistant, an expert in invoice processing and ERPNext automation.

Your expertise includes:
- Invoice OCR processing and accuracy improvement
- ERPNext Purchase Invoice and Journal Entry workflows  
- Expense head categorization and project assignment
- UOM conversions and item mapping
- Supplier learning patterns and automation
- Troubleshooting OCR issues

Your personality:
- Helpful and professional
- Explain technical concepts in simple terms
- Provide actionable solutions
- Ask clarifying questions when needed
- Suggest best practices for better OCR results

Always provide specific, actionable advice related to invoice processing and OCR automation.
"""
        
        # Add context if available
        if context:
            if context.get("current_supplier"):
                base_prompt += f"\n\nCurrent Context: Processing invoice from {context['current_supplier']}"
            
            if context.get("ocr_confidence"):
                base_prompt += f"\nOCR Confidence: {context['ocr_confidence']}%"
            
            if context.get("learning_stage"):
                base_prompt += f"\nLearning Stage: {context['learning_stage']}"
        
        return base_prompt
    
    def _chat_via_raven(self, messages: List[Dict]) -> str:
        """Use Raven's OpenAI integration"""
        try:
            # Import Raven's OpenAI handler
            from raven.api.openai import get_openai_response
            
            response = get_openai_response(
                messages=messages,
                model=self.settings.get("model", "gpt-3.5-turbo")
            )
            
            return response.get("choices", [{}])[0].get("message", {}).get("content", "No response received")
            
        except ImportError:
            # Fallback to direct OpenAI if Raven not available
            return self._chat_direct_openai(messages)
    
    def _chat_direct_openai(self, messages: List[Dict]) -> str:
        """Direct OpenAI API integration"""
        import openai
        
        openai.api_key = self.settings["api_key"]
        
        response = openai.ChatCompletion.create(
            model=self.settings.get("model", "gpt-3.5-turbo"),
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    def _get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history for context"""
        try:
            history = frappe.get_all(
                "Chat History",
                filters={"conversation_id": conversation_id},
                fields=["user_message", "assistant_response"],
                order_by="creation desc",
                limit=10
            )
            
            messages = []
            for entry in reversed(history):
                messages.extend([
                    {"role": "user", "content": entry.user_message},
                    {"role": "assistant", "content": entry.assistant_response}
                ])
            
            return messages
        except:
            return []
    
    def _save_to_history(self, conversation_id: str, user_message: str, response: str):
        """Save conversation to history"""
        try:
            frappe.get_doc({
                "doctype": "Chat History",
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_response": response
            }).insert(ignore_permissions=True)
            frappe.db.commit()
        except:
            pass
    
    def get_ocr_help(self, issue_type: str, context: Dict = None) -> Dict[str, Any]:
        """Provide specific help for OCR issues"""
        
        help_prompts = {
            "low_accuracy": "The OCR accuracy is low. What can I do to improve text recognition?",
            "handwriting": "I'm processing handwritten bills. What's the best approach?",
            "uom_conversion": "How do I handle complex UOM conversions in invoices?",
            "expense_heads": "I'm confused about expense head categorization. Can you guide me?",
            "learning_not_working": "The system doesn't seem to be learning from my corrections. What's wrong?",
            "supplier_patterns": "How can I improve supplier-specific automation?",
            "project_assignment": "Help me with automatic project assignment for invoices."
        }
        
        prompt = help_prompts.get(issue_type, f"I need help with: {issue_type}")
        
        return self.chat(prompt, context)
    
    def explain_ocr_results(self, ocr_data: Dict[str, Any]) -> Dict[str, Any]:
        """Explain OCR processing results to the user"""
        
        explanation_prompt = f"""
Please explain these OCR results in simple terms:

OCR Data:
{json.dumps(ocr_data, indent=2)}

Help the user understand:
1. What was successfully extracted
2. What might need correction
3. Confidence levels and what they mean
4. Suggestions for improving accuracy
5. Next steps in the process
"""
        
        return self.chat(explanation_prompt)

# API Functions for frontend integration
@frappe.whitelist()
def chat_with_assistant(message: str, context: str = None):
    """API endpoint for chatbot interaction"""
    
    assistant = FuzzyWaffleAssistant()
    
    # Parse context if provided
    context_data = json.loads(context) if context else {}
    
    response = assistant.chat(message, context_data)
    
    return response

@frappe.whitelist() 
def get_ocr_help(issue_type: str, context: str = None):
    """API endpoint for specific OCR help"""
    
    assistant = FuzzyWaffleAssistant()
    
    context_data = json.loads(context) if context else {}
    
    response = assistant.get_ocr_help(issue_type, context_data)
    
    return response

@frappe.whitelist()
def explain_results(ocr_data: str):
    """API endpoint to explain OCR results"""
    
    assistant = FuzzyWaffleAssistant()
    
    ocr_data_parsed = json.loads(ocr_data)
    
    response = assistant.explain_ocr_results(ocr_data_parsed)
    
    return response

@frappe.whitelist()
def check_assistant_status():
    """Check if assistant is configured and available"""
    
    assistant = FuzzyWaffleAssistant()
    
    return {
        "enabled": assistant.settings.get("enabled", False),
        "source": assistant.settings.get("source", "none"),
        "model": assistant.settings.get("model", "Not configured")
    }