import frappe
from frappe import _
import json

@frappe.whitelist()
def get_manual_notes_interface(ocr_processor_id):
    """Get the manual notes interface data for an OCR processor"""
    try:
        # Get OCR processor details
        ocr_doc = frappe.get_doc("Invoice OCR Processor", ocr_processor_id)
        
        # Get attached file info
        file_info = None
        if ocr_doc.invoice_file:
            try:
                file_doc = frappe.get_doc("File", ocr_doc.invoice_file)
                file_info = {
                    "name": file_doc.name,
                    "file_name": file_doc.file_name,
                    "file_url": file_doc.file_url,
                    "file_size": file_doc.file_size
                }
            except:
                pass
        
        # Get existing manual notes for this invoice
        existing_notes = frappe.get_all("OCR Notes",
            filters={"original_ocr_processor": ocr_processor_id},
            fields=["name", "note_text", "context_type", "linked_field", "confidence_impact"],
            order_by="creation desc"
        )
        
        return {
            "success": True,
            "ocr_processor": {
                "name": ocr_doc.name,
                "supplier": ocr_doc.supplier,
                "processing_status": ocr_doc.processing_status,
                "confidence_score": ocr_doc.confidence_score,
                "extracted_text": ocr_doc.extracted_text[:500] if ocr_doc.extracted_text else ""
            },
            "file_info": file_info,
            "existing_notes": existing_notes,
            "context_types": [
                {"value": "project", "label": "Project Assignment"},
                {"value": "item", "label": "Item Classification"}, 
                {"value": "payment", "label": "Payment Terms"},
                {"value": "expense_head", "label": "Expense Head"},
                {"value": "supplier", "label": "Supplier Information"},
                {"value": "general", "label": "General Notes"}
            ]
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting manual notes interface: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def save_manual_notes_batch(ocr_processor_id, notes_data):
    """Save multiple manual notes at once"""
    try:
        if isinstance(notes_data, str):
            notes_data = json.loads(notes_data)
        
        # Get OCR processor
        ocr_doc = frappe.get_doc("Invoice OCR Processor", ocr_processor_id)
        
        saved_notes = []
        
        for note_data in notes_data:
            if not note_data.get("note_text", "").strip():
                continue
                
            # Create OCR Note
            note_doc = frappe.new_doc("OCR Notes")
            note_doc.original_ocr_processor = ocr_processor_id
            note_doc.invoice_file = ocr_doc.invoice_file
            note_doc.note_text = note_data.get("note_text", "")
            note_doc.context_type = note_data.get("context_type", "general")
            note_doc.linked_field = note_data.get("linked_field", "")
            
            # Set PDF path
            if ocr_doc.invoice_file:
                try:
                    file_doc = frappe.get_doc("File", ocr_doc.invoice_file)
                    note_doc.scanned_pdf_path = file_doc.file_url
                except:
                    pass
            
            note_doc.insert()
            
            saved_notes.append({
                "note_id": note_doc.name,
                "note_text": note_doc.note_text,
                "context_type": note_doc.context_type,
                "confidence_impact": note_doc.confidence_impact
            })
        
        # Update OCR processor to indicate manual notes were added
        ocr_doc.has_manual_notes = 1
        ocr_doc.manual_notes_count = len(saved_notes)
        
        # Recalculate confidence with manual notes boost
        original_confidence = ocr_doc.confidence_score or 0
        total_boost = sum([note.get("confidence_impact", 0) for note in saved_notes])
        
        # Apply boost but cap at 95% max confidence
        new_confidence = min(original_confidence + (total_boost / len(saved_notes)), 95)
        ocr_doc.confidence_score = new_confidence
        
        ocr_doc.save()
        
        return {
            "success": True,
            "saved_notes": saved_notes,
            "confidence_boost": new_confidence - original_confidence,
            "new_confidence": new_confidence,
            "message": f"Saved {len(saved_notes)} manual notes successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error saving manual notes batch: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_similar_patterns_preview(note_text, context_type, supplier=None):
    """Preview similar patterns before saving a manual note"""
    try:
        # Find similar notes
        similar_notes = []
        
        if len(note_text.strip()) < 3:
            return {"success": True, "similar_notes": []}
        
        # Search for similar note text
        search_query = f"%{note_text.lower()}%"
        
        base_query = """
            SELECT ocr_n.name, ocr_n.note_text, ocr_n.context_type, 
                   ocr_n.linked_field, ocr_n.confidence_impact, ocr_n.times_referenced,
                   ocr_p.supplier, ocr_p.creation as processing_date
            FROM `tabOCR Notes` ocr_n
            LEFT JOIN `tabInvoice OCR Processor` ocr_p ON ocr_n.original_ocr_processor = ocr_p.name
            WHERE ocr_n.note_text LIKE %s
        """
        
        filters = [search_query]
        
        if context_type:
            base_query += " AND ocr_n.context_type = %s"
            filters.append(context_type)
            
        if supplier:
            base_query += " AND ocr_p.supplier = %s"
            filters.append(supplier)
        
        base_query += " ORDER BY ocr_n.times_referenced DESC, ocr_n.creation DESC LIMIT 10"
        
        results = frappe.db.sql(base_query, filters, as_dict=True)
        
        # Calculate similarity scores if fuzzywuzzy is available
        try:
            from fuzzywuzzy import fuzz
            
            for result in results:
                similarity = fuzz.ratio(note_text.lower(), result.note_text.lower())
                result["similarity_score"] = similarity
                result["is_high_similarity"] = similarity > 80
                
        except ImportError:
            # Fallback without fuzzy matching
            for result in results:
                result["similarity_score"] = 75  # Default similarity
                result["is_high_similarity"] = False
        
        return {
            "success": True,
            "similar_notes": results,
            "found_count": len(results)
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting similar patterns preview: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def apply_historical_note_pattern(note_id, current_ocr_processor):
    """Apply a historical note pattern to current processing"""
    try:
        # Get the historical note
        historical_note = frappe.get_doc("OCR Notes", note_id)
        
        # Get current OCR processor
        ocr_doc = frappe.get_doc("Invoice OCR Processor", current_ocr_processor)
        
        # Create new note based on historical pattern
        new_note = frappe.new_doc("OCR Notes")
        new_note.original_ocr_processor = current_ocr_processor
        new_note.invoice_file = ocr_doc.invoice_file
        new_note.note_text = historical_note.note_text
        new_note.context_type = historical_note.context_type
        new_note.linked_field = historical_note.linked_field
        
        # Set confidence based on historical usage
        base_confidence = historical_note.confidence_impact or 60
        usage_boost = min((historical_note.times_referenced or 0) * 2, 20)
        new_note.confidence_impact = min(base_confidence + usage_boost, 95)
        
        # Get PDF path
        if ocr_doc.invoice_file:
            try:
                file_doc = frappe.get_doc("File", ocr_doc.invoice_file)
                new_note.scanned_pdf_path = file_doc.file_url
            except:
                pass
        
        new_note.insert()
        
        # Update historical note usage counter
        historical_note.increment_usage_counter()
        
        # Update current OCR processor
        ocr_doc.confidence_score = min((ocr_doc.confidence_score or 0) + new_note.confidence_impact, 95)
        ocr_doc.has_manual_notes = 1
        ocr_doc.manual_notes_count = (ocr_doc.manual_notes_count or 0) + 1
        ocr_doc.save()
        
        return {
            "success": True,
            "new_note_id": new_note.name,
            "confidence_boost": new_note.confidence_impact,
            "message": "Historical pattern applied successfully"
        }
        
    except Exception as e:
        frappe.log_error(f"Error applying historical note pattern: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@frappe.whitelist()
def get_notes_analytics(supplier=None, date_range=30):
    """Get analytics on manual notes usage"""
    try:
        # Base query for notes analytics
        conditions = []
        values = []
        
        if supplier:
            conditions.append("ocr_p.supplier = %s")
            values.append(supplier)
        
        if date_range:
            conditions.append("ocr_n.creation >= DATE_SUB(CURDATE(), INTERVAL %s DAY)")
            values.append(date_range)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Get notes statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_notes,
                AVG(ocr_n.confidence_impact) as avg_confidence_impact,
                SUM(ocr_n.times_referenced) as total_references,
                COUNT(DISTINCT ocr_n.context_type) as unique_contexts,
                COUNT(DISTINCT ocr_p.supplier) as suppliers_with_notes
            FROM `tabOCR Notes` ocr_n
            LEFT JOIN `tabInvoice OCR Processor` ocr_p ON ocr_n.original_ocr_processor = ocr_p.name
            {where_clause}
        """
        
        stats = frappe.db.sql(stats_query, values, as_dict=True)[0]
        
        # Get context type breakdown
        context_query = f"""
            SELECT 
                ocr_n.context_type,
                COUNT(*) as count,
                AVG(ocr_n.confidence_impact) as avg_impact
            FROM `tabOCR Notes` ocr_n
            LEFT JOIN `tabInvoice OCR Processor` ocr_p ON ocr_n.original_ocr_processor = ocr_p.name
            {where_clause}
            GROUP BY ocr_n.context_type
            ORDER BY count DESC
        """
        
        context_breakdown = frappe.db.sql(context_query, values, as_dict=True)
        
        # Get top patterns (most referenced)
        top_patterns_query = f"""
            SELECT 
                ocr_n.note_text,
                ocr_n.context_type,
                ocr_n.times_referenced,
                ocr_n.confidence_impact,
                ocr_p.supplier
            FROM `tabOCR Notes` ocr_n
            LEFT JOIN `tabInvoice OCR Processor` ocr_p ON ocr_n.original_ocr_processor = ocr_p.name
            {where_clause}
            ORDER BY ocr_n.times_referenced DESC, ocr_n.confidence_impact DESC
            LIMIT 10
        """
        
        top_patterns = frappe.db.sql(top_patterns_query, values, as_dict=True)
        
        return {
            "success": True,
            "statistics": stats,
            "context_breakdown": context_breakdown,
            "top_patterns": top_patterns,
            "date_range": date_range,
            "supplier": supplier
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting notes analytics: {e}")
        return {
            "success": False,
            "error": str(e)
        }