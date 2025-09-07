import frappe
import pytesseract
from PIL import Image
import cv2
import numpy as np
import re
import json
from typing import Dict, List, Any, Optional
from pdf2image import convert_from_path
import tempfile
import os

class OCRProcessor:
    def __init__(self):
        self.settings = self.get_ocr_settings()
        
    def get_ocr_settings(self) -> Dict[str, Any]:
        """Get OCR settings from database or use defaults"""
        try:
            settings = frappe.get_single("OCR Settings")
            return {
                "engine": settings.ocr_engine or "tesseract",
                "confidence_threshold": settings.confidence_threshold or 60,
                "auto_submit_threshold": settings.auto_submit_threshold or 95
            }
        except:
            return {
                "engine": "tesseract",
                "confidence_threshold": 60,
                "auto_submit_threshold": 95
            }
    
    def extract_text_from_file(self, file_url: str) -> str:
        """Extract text from uploaded file (PDF or image)"""
        file_path = frappe.get_site_path(file_url.lstrip('/'))
        
        if file_path.lower().endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        else:
            return self.extract_text_from_image(file_path)
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300)
            
            for i, image in enumerate(images):
                # Process each page
                img_path = os.path.join(temp_dir, f"page_{i}.png")
                image.save(img_path, 'PNG')
                text += self.extract_text_from_image(img_path) + "\n"
        
        return text
    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from image using OCR"""
        # Preprocess image
        processed_image = self.preprocess_image(image_path)
        
        # Extract text using Tesseract
        text = pytesseract.image_to_string(processed_image, config='--psm 6')
        
        return text
    
    def preprocess_image(self, image_path: str) -> np.ndarray:
        """Preprocess image for better OCR accuracy, optimized for handwritten bills"""
        # Read image
        img = cv2.imread(image_path)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Enhanced preprocessing for handwritten text
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply adaptive thresholding for varying lighting conditions
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Morphological operations to clean up handwritten text
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        
        # Close gaps in handwritten characters
        closed = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=1)
        
        # Remove small noise
        opening = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel, iterations=1)
        
        # Dilation to make handwritten text bolder for better recognition
        dilated = cv2.dilate(opening, kernel, iterations=1)
        
        return dilated
    
    def extract_text_with_handwriting_support(self, image_path: str) -> str:
        """Extract text with enhanced handwriting recognition"""
        # Preprocess image
        processed_image = self.preprocess_image(image_path)
        
        # Try multiple OCR configurations for better handwriting recognition
        ocr_configs = [
            '--psm 6 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,₹/-:() ',
            '--psm 4 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,₹/-:() ',
            '--psm 8 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,₹/-:() ',
            '--psm 13'  # Raw line. Treat the image as a single text line
        ]
        
        best_text = ""
        highest_confidence = 0
        
        for config in ocr_configs:
            try:
                # Get text with confidence
                data = pytesseract.image_to_data(
                    processed_image, 
                    config=config, 
                    output_type=pytesseract.Output.DICT
                )
                
                # Calculate average confidence
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                if avg_confidence > highest_confidence:
                    highest_confidence = avg_confidence
                    text = pytesseract.image_to_string(processed_image, config=config)
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text
                        
            except Exception as e:
                continue
        
        return best_text if best_text else pytesseract.image_to_string(processed_image)
    
    def extract_invoice_data(self, ocr_text: str) -> Dict[str, Any]:
        """Extract structured invoice data from OCR text"""
        data = {
            "invoice_number": self.extract_invoice_number(ocr_text),
            "invoice_date": self.extract_date(ocr_text),
            "total_amount": self.extract_total_amount(ocr_text),
            "items": self.extract_line_items(ocr_text),
            "payment_terms": self.extract_payment_terms(ocr_text),
            "tax_info": self.extract_tax_info(ocr_text)
        }
        
        return data
    
    def extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text"""
        patterns = [
            r'Invoice\s*(?:No|Number|#)?\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'Bill\s*(?:No|Number)?\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'Inv\s*[:.]?\s*([A-Z0-9\-/]+)',
            r'(?:Invoice|Bill|Inv)\s*([A-Z0-9\-/]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def extract_date(self, text: str) -> Optional[str]:
        """Extract date from text"""
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
            r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Convert to standard format
                return self.standardize_date(date_str)
        
        return None
    
    def standardize_date(self, date_str: str) -> str:
        """Convert date to YYYY-MM-DD format"""
        from dateutil import parser
        try:
            parsed_date = parser.parse(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return date_str
    
    def extract_total_amount(self, text: str) -> Optional[float]:
        """Extract total amount from text"""
        patterns = [
            r'Total\s*[:.]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+\.?\d*)',
            r'Grand\s*Total\s*[:.]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+\.?\d*)',
            r'Amount\s*Payable\s*[:.]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+\.?\d*)',
            r'Net\s*Amount\s*[:.]?\s*(?:₹|Rs\.?|INR)?\s*([0-9,]+\.?\d*)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    return float(amount_str)
                except:
                    continue
        
        return None
    
    def extract_line_items(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from invoice text"""
        items = []
        
        # Pattern for line items (description, quantity, rate, amount)
        item_pattern = r'([A-Za-z\s\-]+)\s+(\d+\.?\d*)\s*(?:Pcs|Kg|Lt|Nos|Box)?\s+(?:₹|Rs\.?)?\s*(\d+\.?\d*)\s+(?:₹|Rs\.?)?\s*(\d+\.?\d*)'
        
        matches = re.finditer(item_pattern, text)
        
        for match in matches:
            item = {
                "description": match.group(1).strip(),
                "quantity": float(match.group(2)),
                "rate": float(match.group(3)),
                "amount": float(match.group(4))
            }
            
            # Extract UOM if present
            uom_match = re.search(r'(\d+\.?\d*)\s*(Pcs|Kg|Lt|Nos|Box|Unit)', match.group(0), re.IGNORECASE)
            if uom_match:
                item["uom"] = uom_match.group(2)
            
            items.append(item)
        
        return items
    
    def extract_payment_terms(self, text: str) -> Optional[str]:
        """Extract payment terms from text"""
        patterns = [
            r'Payment\s*Terms?\s*[:.]?\s*([A-Za-z0-9\s]+)',
            r'(?:Net|Credit)\s*(\d+\s*Days?)',
            r'Due\s*(?:in|within)\s*(\d+\s*Days?)',
            r'(Cash|COD|Credit)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_tax_info(self, text: str) -> Dict[str, Any]:
        """Extract tax information from text"""
        tax_info = {}
        
        # GST pattern
        gst_pattern = r'GST[IN]*\s*[:.]?\s*([A-Z0-9]+)'
        gst_match = re.search(gst_pattern, text, re.IGNORECASE)
        if gst_match:
            tax_info["gstin"] = gst_match.group(1)
        
        # Tax amounts
        tax_patterns = {
            "cgst": r'CGST\s*(?:@\s*\d+%?)?\s*[:.]?\s*(?:₹|Rs\.?)?\s*([0-9,]+\.?\d*)',
            "sgst": r'SGST\s*(?:@\s*\d+%?)?\s*[:.]?\s*(?:₹|Rs\.?)?\s*([0-9,]+\.?\d*)',
            "igst": r'IGST\s*(?:@\s*\d+%?)?\s*[:.]?\s*(?:₹|Rs\.?)?\s*([0-9,]+\.?\d*)'
        }
        
        for tax_type, pattern in tax_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(',', '')
                try:
                    tax_info[tax_type] = float(amount_str)
                except:
                    pass
        
        return tax_info

@frappe.whitelist()
def test_ocr_extraction(file_url: str) -> Dict[str, Any]:
    """Test OCR extraction on a file"""
    processor = OCRProcessor()
    
    # Extract text
    ocr_text = processor.extract_text_from_file(file_url)
    
    # Extract structured data
    invoice_data = processor.extract_invoice_data(ocr_text)
    
    return {
        "raw_text": ocr_text[:500],  # First 500 chars for preview
        "extracted_data": invoice_data
    }