import frappe
from frappe.model.document import Document
import json
from typing import Dict, List, Any

class InvoiceOCRProcessor(Document):
    def validate(self):
        self.calculate_total_amount()
        self.update_automation_metrics()
        
    def calculate_total_amount(self):
        total = 0
        if self.extracted_items:
            for item in self.extracted_items:
                if item.ocr_amount:
                    total += float(item.ocr_amount)
        self.total_amount = total
    
    def update_automation_metrics(self):
        if not self.automation_percentage:
            self.automation_percentage = 0
        
        if not self.user_interventions_count:
            self.user_interventions_count = 0
            
        # Update processing stage based on supplier history
        supplier_history = get_supplier_processing_count(self.supplier)
        
        if supplier_history <= 25:
            self.processing_stage = "Stage 1"
            self.automation_percentage = 40
        elif supplier_history <= 50:
            self.processing_stage = "Stage 2"
            self.automation_percentage = 60
        elif supplier_history <= 100:
            self.processing_stage = "Stage 3"
            self.automation_percentage = 80
        else:
            self.processing_stage = "Stage 4"
            self.automation_percentage = 95
    
    def process_ocr_data(self, ocr_text: str) -> Dict[str, Any]:
        """Process OCR text and extract invoice data"""
        from fuzzy_waffle_ocr.ocr.processor import OCRProcessor
        
        processor = OCRProcessor()
        extracted_data = processor.extract_invoice_data(ocr_text)
        
        # Apply learning patterns
        self.apply_learning_patterns(extracted_data)
        
        return extracted_data
    
    def apply_learning_patterns(self, extracted_data: Dict[str, Any]):
        """Apply learned patterns from supplier history"""
        from fuzzy_waffle_ocr.learning.supplier_learning import SupplierLearning
        
        learning = SupplierLearning(self.supplier)
        
        # Apply item mapping patterns
        if extracted_data.get('items'):
            for item in extracted_data['items']:
                mapped_item = learning.get_item_mapping(item.get('description'))
                if mapped_item:
                    item['erpnext_item'] = mapped_item['item_code']
                    item['confidence'] = mapped_item['confidence']
                    
                    # Apply UOM conversion
                    uom_conversion = learning.get_uom_conversion(
                        item.get('description'),
                        item.get('quantity'),
                        item.get('uom')
                    )
                    if uom_conversion:
                        item['erpnext_quantity'] = uom_conversion['erpnext_quantity']
                        item['erpnext_uom'] = uom_conversion['erpnext_uom']
                        item['erpnext_rate'] = uom_conversion['erpnext_rate']
        
        # Apply payment terms pattern
        if extracted_data.get('payment_terms'):
            mapped_terms = learning.get_payment_terms_mapping(
                extracted_data['payment_terms']
            )
            if mapped_terms:
                extracted_data['erpnext_payment_terms'] = mapped_terms
        
        # Suggest project
        project_suggestion = learning.suggest_project(extracted_data.get('items', []))
        if project_suggestion:
            self.suggested_project = project_suggestion['project']
            self.project_confidence = project_suggestion['confidence']
            
        self.learning_confidence = learning.get_overall_confidence()
    
    def create_purchase_invoice(self) -> str:
        """Create Purchase Invoice from OCR data"""
        from fuzzy_waffle_ocr.utils.document_creator import DocumentCreator
        
        creator = DocumentCreator()
        
        # Get mandatory fields
        mandatory_fields = creator.get_dynamic_mandatory_fields("Purchase Invoice")
        
        # Prepare data
        invoice_data = {
            "doctype": "Purchase Invoice",
            "supplier": self.supplier,
            "bill_no": self.invoice_number,
            "bill_date": self.invoice_date,
            "payment_terms_template": self.payment_terms,
            "project": self.suggested_project if self.project_confidence > 80 else None,
            "items": []
        }
        
        # Add items
        for item in self.extracted_items:
            invoice_data["items"].append({
                "item_code": item.final_erpnext_item or item.suggested_erpnext_item,
                "qty": item.erpnext_quantity or item.ocr_quantity,
                "uom": item.erpnext_uom,
                "rate": item.erpnext_rate or item.ocr_rate
            })
        
        # Check for missing mandatory fields
        missing_fields = creator.validate_mandatory_fields(invoice_data, mandatory_fields)
        
        if missing_fields:
            self.missing_fields_status = "Pending User Input"
            self.mandatory_fields_data = json.dumps(missing_fields)
            frappe.msgprint(f"Missing mandatory fields: {', '.join([f['label'] for f in missing_fields])}")
            return None
        
        # Create the invoice
        invoice = creator.create_document("Purchase Invoice", invoice_data)
        
        self.created_document_type = "Purchase Invoice"
        self.created_document = invoice.name
        self.ocr_status = "Completed"
        self.missing_fields_status = "Complete"
        
        return invoice.name
    
    def create_journal_entry(self) -> str:
        """Create Journal Entry from OCR data"""
        from fuzzy_waffle_ocr.utils.document_creator import DocumentCreator
        from fuzzy_waffle_ocr.learning.journal_learning import JournalLearning
        
        creator = DocumentCreator()
        learning = JournalLearning(self.supplier)
        
        # Get account patterns
        accounts = []
        for item in self.extracted_items:
            account_head = learning.get_account_mapping(item.ocr_item_text)
            if account_head:
                accounts.append({
                    "account": account_head,
                    "debit_in_account_currency": item.ocr_amount if self.document_type == "Journal Entry" else 0,
                    "credit_in_account_currency": 0 if self.document_type == "Journal Entry" else item.ocr_amount,
                    "project": self.suggested_project
                })
        
        # Add balancing entry
        mode_of_payment = learning.get_mode_of_payment()
        accounts.append({
            "account": mode_of_payment,
            "credit_in_account_currency": self.total_amount if self.document_type == "Journal Entry" else 0,
            "debit_in_account_currency": 0 if self.document_type == "Journal Entry" else self.total_amount
        })
        
        journal_data = {
            "doctype": "Journal Entry",
            "voucher_type": "Journal Entry",
            "posting_date": self.invoice_date or frappe.utils.today(),
            "accounts": accounts,
            "user_remark": f"Invoice: {self.invoice_number}"
        }
        
        journal = creator.create_document("Journal Entry", journal_data)
        
        self.journal_entry_created = journal.name
        self.created_document_type = "Journal Entry"
        self.created_document = journal.name
        self.ocr_status = "Completed"
        
        return journal.name
    
    def create_payment_entry(self, purchase_invoice: str) -> str:
        """Create Payment Entry for Purchase Invoice"""
        from fuzzy_waffle_ocr.learning.payment_learning import PaymentLearning
        
        learning = PaymentLearning(self.supplier)
        payment_pattern = learning.get_payment_pattern()
        
        if payment_pattern['confidence'] > 90:
            payment_entry = frappe.get_doc({
                "doctype": "Payment Entry",
                "payment_type": "Pay",
                "party_type": "Supplier",
                "party": self.supplier,
                "mode_of_payment": payment_pattern['preferred_mode'],
                "paid_from": payment_pattern['bank_account'],
                "paid_amount": self.total_amount,
                "received_amount": self.total_amount,
                "reference_no": purchase_invoice,
                "reference_date": self.invoice_date,
                "project": self.suggested_project,
                "references": [{
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": purchase_invoice,
                    "allocated_amount": self.total_amount
                }]
            })
            
            if payment_pattern['auto_submit']:
                payment_entry.insert()
                payment_entry.submit()
            else:
                payment_entry.insert()
            
            self.payment_entry_created = payment_entry.name
            return payment_entry.name
        
        return None

def get_supplier_processing_count(supplier: str) -> int:
    """Get count of processed invoices for a supplier"""
    return frappe.db.count("Invoice OCR Processor", {"supplier": supplier, "ocr_status": "Completed"})

@frappe.whitelist()
def process_ocr_upload(file_url: str, supplier: str, document_type: str) -> Dict[str, Any]:
    """Process uploaded invoice file"""
    from fuzzy_waffle_ocr.ocr.processor import OCRProcessor
    
    processor = OCRProcessor()
    
    # Extract text from file
    ocr_text = processor.extract_text_from_file(file_url)
    
    # Create OCR processor document
    ocr_doc = frappe.get_doc({
        "doctype": "Invoice OCR Processor",
        "supplier": supplier,
        "document_type": document_type,
        "ocr_status": "Processing"
    })
    
    # Process OCR data
    extracted_data = ocr_doc.process_ocr_data(ocr_text)
    
    # Update document with extracted data
    ocr_doc.update(extracted_data)
    ocr_doc.insert()
    
    return {
        "name": ocr_doc.name,
        "status": "success",
        "confidence": ocr_doc.learning_confidence,
        "data": extracted_data
    }