import frappe
from frappe.model.document import Document
from frappe.utils import now
import json

class OCRNotes(Document):
    def before_insert(self):
        """Set default values before inserting"""
        if not self.processing_date:
            self.processing_date = now()
        
        if not self.created_by_user:
            self.created_by_user = frappe.session.user
    
    def after_insert(self):
        """After saving manual note, apply to learning algorithm"""
        self.apply_to_learning_algorithm()
        
    def apply_to_learning_algorithm(self):
        """Apply this manual note to the learning system"""
        try:
            # Find similar patterns in historical notes
            similar_notes = self.find_similar_patterns()
            
            if similar_notes:
                # Calculate pattern similarity score
                max_similarity = max([note.get('similarity', 0) for note in similar_notes])
                self.pattern_similarity_score = max_similarity
                
                # If highly similar pattern exists, boost confidence
                if max_similarity > 80:
                    self.confidence_impact = min(max_similarity, 95)
                else:
                    self.confidence_impact = 60  # Default boost for new patterns
            else:
                self.confidence_impact = 60  # New pattern
            
            # Mark as applied to learning
            self.applied_to_learning = 1
            
            # Update learning data in Supplier Item Mapping
            self.update_supplier_mapping()
            
            # Save changes
            self.save()
            
        except Exception as e:
            frappe.log_error(f"Error applying OCR note to learning: {e}")
    
    def find_similar_patterns(self):
        """Find similar manual notes for pattern matching"""
        try:
            # Get all notes with same context type
            similar_context_notes = frappe.get_all("OCR Notes",
                filters={
                    "context_type": self.context_type,
                    "name": ["!=", self.name]
                },
                fields=["name", "note_text", "linked_field", "confidence_impact"]
            )
            
            similar_patterns = []
            
            # Use fuzzy matching to find similar note texts
            from fuzzywuzzy import fuzz
            
            for note in similar_context_notes:
                similarity = fuzz.ratio(self.note_text.lower(), note.note_text.lower())
                if similarity > 70:  # 70% similarity threshold
                    similar_patterns.append({
                        "name": note.name,
                        "similarity": similarity,
                        "linked_field": note.linked_field,
                        "confidence_impact": note.confidence_impact
                    })
            
            return sorted(similar_patterns, key=lambda x: x['similarity'], reverse=True)
            
        except ImportError:
            frappe.log_error("fuzzywuzzy not installed - manual note pattern matching disabled")
            return []
        except Exception as e:
            frappe.log_error(f"Error finding similar patterns: {e}")
            return []
    
    def update_supplier_mapping(self):
        """Update supplier item mapping with manual note data"""
        try:
            # Get supplier from linked OCR processor or Purchase Invoice
            supplier = None
            
            if self.original_ocr_processor:
                ocr_doc = frappe.get_doc("Invoice OCR Processor", self.original_ocr_processor)
                supplier = ocr_doc.supplier
            elif self.linked_purchase_invoice:
                pi_doc = frappe.get_doc("Purchase Invoice", self.linked_purchase_invoice)
                supplier = pi_doc.supplier
            
            if not supplier:
                return
            
            # Find or create supplier mapping
            supplier_mapping = frappe.get_all("Supplier Item Mapping",
                filters={"supplier": supplier},
                limit=1
            )
            
            if supplier_mapping:
                mapping_doc = frappe.get_doc("Supplier Item Mapping", supplier_mapping[0].name)
            else:
                # Create new mapping
                mapping_doc = frappe.new_doc("Supplier Item Mapping")
                mapping_doc.supplier = supplier
                mapping_doc.total_invoices_processed = 1
                mapping_doc.insert()
            
            # Add manual note data to supplier patterns
            self.add_note_to_supplier_patterns(mapping_doc)
            
        except Exception as e:
            frappe.log_error(f"Error updating supplier mapping: {e}")
    
    def add_note_to_supplier_patterns(self, supplier_mapping):
        """Add this manual note as a learning pattern"""
        try:
            # Create pattern data structure
            pattern_data = {
                "type": "manual_note",
                "context_type": self.context_type,
                "note_text": self.note_text,
                "linked_field": self.linked_field,
                "confidence_boost": self.confidence_impact,
                "times_used": 1,
                "last_used": self.processing_date,
                "created_from_note": self.name
            }
            
            # Get existing manual note patterns
            manual_patterns = []
            if supplier_mapping.custom_patterns:
                try:
                    existing_patterns = json.loads(supplier_mapping.custom_patterns)
                    manual_patterns = existing_patterns.get("manual_notes", [])
                except:
                    pass
            
            # Add new pattern
            manual_patterns.append(pattern_data)
            
            # Update supplier mapping
            all_patterns = {
                "manual_notes": manual_patterns,
                "last_updated": now()
            }
            
            supplier_mapping.custom_patterns = json.dumps(all_patterns)
            supplier_mapping.save()
            
            frappe.msgprint(f"✅ Manual note added to learning system for supplier {supplier_mapping.supplier}")
            
        except Exception as e:
            frappe.log_error(f"Error adding note to supplier patterns: {e}")
    
    def increment_usage_counter(self):
        """Increment usage counter when this pattern is referenced"""
        self.times_referenced = (self.times_referenced or 0) + 1
        self.last_used_date = frappe.utils.today()
        self.save()
    
    @frappe.whitelist()
    def get_related_invoices(self):
        """Get all invoices that might benefit from this manual note"""
        try:
            related_invoices = []
            
            # Find OCR processors with similar patterns
            if self.context_type == "project":
                # Find invoices with similar project-related text
                ocr_processors = frappe.get_all("Invoice OCR Processor",
                    filters={"docstatus": 1},
                    fields=["name", "supplier", "extracted_text", "creation"]
                )
                
                for processor in ocr_processors:
                    if processor.extracted_text and self.note_text.lower() in processor.extracted_text.lower():
                        related_invoices.append({
                            "processor": processor.name,
                            "supplier": processor.supplier,
                            "date": processor.creation,
                            "relevance": "High - Contains similar text pattern"
                        })
            
            return related_invoices
            
        except Exception as e:
            frappe.log_error(f"Error getting related invoices: {e}")
            return []

@frappe.whitelist()
def save_manual_note(invoice_file, note_text, context_type, linked_field=None, ocr_processor=None):
    """API endpoint to save manual OCR note"""
    try:
        # Create new OCR Note
        note_doc = frappe.new_doc("OCR Notes")
        note_doc.invoice_file = invoice_file
        note_doc.note_text = note_text
        note_doc.context_type = context_type
        note_doc.linked_field = linked_field or ""
        
        if ocr_processor:
            note_doc.original_ocr_processor = ocr_processor
            
        # Get file path
        if invoice_file:
            file_doc = frappe.get_doc("File", invoice_file)
            note_doc.scanned_pdf_path = file_doc.file_url
        
        note_doc.insert()
        
        return {
            "success": True,
            "note_id": note_doc.name,
            "message": "Manual note saved successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving manual note: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_invoice_notes(invoice_file):
    """Get all manual notes for an invoice file"""
    try:
        notes = frappe.get_all("OCR Notes",
            filters={"invoice_file": invoice_file},
            fields=["name", "note_text", "context_type", "linked_field", "confidence_impact", "creation"],
            order_by="creation desc"
        )
        
        return {
            "success": True,
            "notes": notes
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def search_historical_notes(search_term, supplier=None, context_type=None):
    """Search through historical manual notes for patterns"""
    try:
        filters = {}
        
        if supplier:
            # Get OCR processors for this supplier
            supplier_processors = frappe.get_all("Invoice OCR Processor",
                filters={"supplier": supplier},
                fields=["name"]
            )
            
            if supplier_processors:
                processor_names = [p.name for p in supplier_processors]
                filters["original_ocr_processor"] = ["in", processor_names]
        
        if context_type:
            filters["context_type"] = context_type
        
        # Search in note text
        if search_term:
            notes = frappe.db.sql("""
                SELECT name, note_text, context_type, linked_field, 
                       confidence_impact, times_referenced, creation
                FROM `tabOCR Notes`
                WHERE note_text LIKE %s
                {supplier_filter}
                {context_filter}
                ORDER BY times_referenced DESC, creation DESC
                LIMIT 20
            """.format(
                supplier_filter="AND original_ocr_processor IN %(processors)s" if supplier else "",
                context_filter="AND context_type = %(context_type)s" if context_type else ""
            ), {
                "search_term": f"%{search_term}%",
                "processors": processor_names if supplier else [],
                "context_type": context_type
            }, as_dict=True)
        else:
            notes = frappe.get_all("OCR Notes",
                filters=filters,
                fields=["name", "note_text", "context_type", "linked_field", 
                       "confidence_impact", "times_referenced", "creation"],
                order_by="times_referenced desc, creation desc",
                limit=20
            )
        
        return {
            "success": True,
            "notes": notes,
            "count": len(notes)
        }
        
    except Exception as e:
        frappe.log_error(f"Error searching historical notes: {e}")
        return {
            "success": False,
            "error": str(e)
        }