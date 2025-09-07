# Fuzzy Waffle OCR

Intelligent OCR-based invoice processing for ERPNext with machine learning capabilities.

## Features
- 🧠 **Learning System**: Remembers supplier-specific patterns
- 🔄 **UOM Conversion**: Intelligent unit conversions
- 📄 **Multi-Document Support**: Purchase Invoice, Journal Entry, Purchase Receipt
- 🎯 **95% Automation**: After 100+ invoices per supplier
- 📊 **Historical Learning**: Learns from 3 years of data

## Installation

```bash
bench get-app https://github.com/lato-tech/fuzzy-waffle-ocr.git
bench --site your-site install-app fuzzy_waffle_ocr
```

## Quick Start

1. Navigate to Purchase Invoice or Journal Entry
2. Click "OCR Upload" button
3. Upload invoice PDF/image
4. Review and confirm extracted data
5. System learns from your corrections

## Requirements
- ERPNext v14+
- Python 3.8+
- Tesseract OCR installed

## License
MIT