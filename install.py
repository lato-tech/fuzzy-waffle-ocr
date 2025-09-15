import frappe

def after_install():
    """Run after app installation"""
    
    # Create default OCR Settings
    if not frappe.db.exists("OCR Settings", "OCR Settings"):
        ocr_settings = frappe.get_doc({
            "doctype": "OCR Settings",
            "ocr_engine": "tesseract",
            "confidence_threshold": 75,
            "auto_submit_threshold": 95,
            "learning_enabled": 1,
            "historical_data_processed": 0
        })
        ocr_settings.insert(ignore_permissions=True)
    
    # Set up permissions
    setup_permissions()
    
    frappe.db.commit()

def setup_permissions():
    """Set up role permissions for OCR doctypes"""
    
    permissions = [
        # Invoice OCR Processor
        {
            "doctype": "Invoice OCR Processor",
            "role": "Accounts User",
            "permlevel": 0,
            "read": 1,
            "write": 1,
            "create": 1
        },
        {
            "doctype": "Invoice OCR Processor", 
            "role": "Accounts Manager",
            "permlevel": 0,
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        },
        
        # Supplier Item Mapping
        {
            "doctype": "Supplier Item Mapping",
            "role": "System Manager",
            "permlevel": 0,
            "read": 1,
            "write": 1,
            "create": 1,
            "delete": 1
        },
        {
            "doctype": "Supplier Item Mapping",
            "role": "Accounts Manager", 
            "permlevel": 0,
            "read": 1,
            "write": 1
        },
        
        # OCR Settings  
        {
            "doctype": "OCR Settings",
            "role": "System Manager",
            "permlevel": 0,
            "read": 1,
            "write": 1
        }
    ]
    
    for perm in permissions:
        if not frappe.db.exists("Custom DocPerm", {
            "parent": perm["doctype"],
            "role": perm["role"], 
            "permlevel": perm["permlevel"]
        }):
            frappe.get_doc({
                "doctype": "Custom DocPerm",
                "parent": perm["doctype"],
                "parenttype": "DocType",
                "parentfield": "permissions",
                **perm
            }).insert(ignore_permissions=True)