# Fuzzy Waffle OCR - Installation Guide

## Prerequisites

### System Requirements
- **ERPNext**: Version 14.0+
- **Python**: 3.8+  
- **Operating System**: Ubuntu 20.04+ / CentOS 8+ / macOS
- **RAM**: Minimum 4GB (8GB recommended)
- **Storage**: 2GB free space

### Dependencies Installation

#### 1. Install OCR Libraries
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-eng
sudo apt install poppler-utils  # For PDF processing
sudo apt install libopencv-dev python3-opencv

# CentOS/RHEL  
sudo yum install tesseract tesseract-langpack-eng
sudo yum install poppler-utils opencv-python

# macOS
brew install tesseract
brew install poppler
```

#### 2. Install Python Libraries
```bash
# Activate your ERPNext environment
source /path/to/frappe-bench/env/bin/activate

# Install required packages
pip install pytesseract
pip install Pillow
pip install opencv-python
pip install fuzzywuzzy
pip install python-Levenshtein
pip install pdf2image
pip install numpy
```

## Installation Steps

### Method 1: Install from GitHub (Recommended)

#### 1. Get the App
```bash
# Navigate to your frappe-bench directory
cd /path/to/frappe-bench

# Get the app from GitHub
bench get-app https://github.com/lato-tech/fuzzy-waffle-ocr.git

# Install the app on your site
bench --site your-site-name install-app fuzzy_waffle_ocr
```

#### 2. Run Migrations
```bash
# Migrate database
bench --site your-site-name migrate

# Clear cache
bench --site your-site-name clear-cache

# Build assets
bench build --app fuzzy_waffle_ocr
```

#### 3. Restart Services
```bash
# Restart bench
bench restart

# Or restart specific services
sudo service supervisor restart  # If using supervisor
```

### Method 2: Manual Installation

#### 1. Clone Repository
```bash
cd /path/to/frappe-bench/apps
git clone https://github.com/lato-tech/fuzzy-waffle-ocr.git
cd fuzzy-waffle-ocr
```

#### 2. Install Dependencies
```bash
pip install -e .
```

#### 3. Install App
```bash
cd /path/to/frappe-bench
bench --site your-site-name install-app fuzzy_waffle_ocr
bench --site your-site-name migrate
```

## Post-Installation Setup

### 1. Configure OCR Settings

Navigate to: **Setup → Fuzzy Waffle OCR → OCR Settings**

```json
{
  "ocr_engine": "tesseract",
  "confidence_threshold": 75,
  "auto_submit_threshold": 95,
  "learning_enabled": true,
  "historical_data_processed": false
}
```

### 2. Migrate Historical Data (Critical Step)

This step teaches the system from your existing data:

```bash
# Navigate to your site
bench --site your-site-name console

# Run migration command
>>> import frappe
>>> frappe.get_doc({
...     "doctype": "Scheduled Job Type", 
...     "method": "fuzzy_waffle_ocr.learning.comprehensive_learning.migrate_comprehensive_learning",
...     "frequency": "Manual"
... }).insert()

# Or run directly
>>> from fuzzy_waffle_ocr.learning.comprehensive_learning import ComprehensiveLearning
>>> learning = ComprehensiveLearning()
>>> learning.learn_from_all_historical_data()
```

**Expected Processing Time**: 5-30 minutes depending on data volume

### 3. Set User Permissions

Grant appropriate roles access to OCR features:

**For Accounts Users:**
- Read access to "Invoice OCR Processor"
- Write access to "Invoice OCR Processor"

**For Accounts Managers:**
- Full access to all OCR doctypes
- Access to OCR Settings

```bash
# Set permissions via bench
bench --site your-site-name set-permission "Invoice OCR Processor" "Accounts User" 0 read,write,create
bench --site your-site-name set-permission "Invoice OCR Processor" "Accounts Manager" 0 permlevel,read,write,create,delete
```

## Verification

### 1. Check Installation
Navigate to: **Modules → Fuzzy Waffle OCR**

You should see:
- Invoice OCR Processor
- Supplier Item Mapping  
- OCR Settings

### 2. Test OCR Upload
1. Go to **Accounts → Purchase Invoice → New**
2. Look for "OCR Upload" button
3. Upload a test invoice PDF/image
4. Verify processing works

### 3. Check Learning Data
Navigate to: **Fuzzy Waffle OCR → Supplier Item Mapping**
- Should show learned patterns from historical data
- Confidence scores should be 70%+

## Troubleshooting

### Common Issues

#### 1. Tesseract Not Found
```
Error: TesseractNotFoundError
```

**Solution:**
```bash
# Check tesseract installation
which tesseract
tesseract --version

# If not found, reinstall
sudo apt install tesseract-ocr

# Set path in environment
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata/
```

#### 2. Permission Denied on File Upload
```
Error: Permission denied accessing file
```

**Solution:**
```bash
# Check file permissions
sudo chown -R frappe:frappe /path/to/frappe-bench/sites/your-site/private/files/
sudo chmod -R 755 /path/to/frappe-bench/sites/your-site/private/files/
```

#### 3. Learning Migration Fails
```
Error: Table doesn't exist or Access denied
```

**Solution:**
```bash
# Run migrations again
bench --site your-site-name migrate --force

# Check if user has proper database permissions
bench --site your-site-name console
>>> frappe.db.sql("SHOW GRANTS FOR CURRENT_USER")
```

#### 4. OCR Processing Slow
**Optimization:**
```bash
# Install faster OCR engine
pip install google-cloud-vision  # If using Google Vision API

# Optimize image processing
# Edit settings: Lower DPI for faster processing
```

### Performance Optimization

#### 1. Database Indexing
```sql
-- Add indexes for faster learning queries
CREATE INDEX idx_supplier_item ON `tabSupplier Item Mapping` (supplier, erpnext_item_code);
CREATE INDEX idx_pi_supplier_date ON `tabPurchase Invoice` (supplier, creation);
CREATE INDEX idx_pi_item_expense ON `tabPurchase Invoice Item` (item_code, expense_account);
```

#### 2. Background Processing
```python
# Use background jobs for heavy processing
frappe.enqueue(
    'fuzzy_waffle_ocr.ocr.processor.process_large_file',
    queue='long',
    file_url=file_url
)
```

## Maintenance

### Regular Tasks

#### 1. Update Learning Data (Monthly)
```bash
# Run learning update
bench --site your-site-name execute fuzzy_waffle_ocr.learning.comprehensive_learning.migrate_comprehensive_learning
```

#### 2. Clean Old OCR Records (Quarterly) 
```python
# Keep only last 6 months of OCR processor records
import frappe
from datetime import datetime, timedelta

cutoff_date = datetime.now() - timedelta(days=180)
old_records = frappe.get_all(
    "Invoice OCR Processor", 
    filters={"creation": ["<", cutoff_date]},
    fields=["name"]
)

for record in old_records:
    frappe.delete_doc("Invoice OCR Processor", record.name)

frappe.db.commit()
```

#### 3. Backup Learning Data
```bash
# Export learning patterns
bench --site your-site-name export-doc "Supplier Item Mapping" --path /backup/learning_data.json
```

## Support & Updates

### Getting Updates
```bash
# Update to latest version
cd /path/to/frappe-bench/apps/fuzzy_waffle_ocr
git pull origin main

# Run migrations
bench --site your-site-name migrate

# Rebuild assets  
bench build --app fuzzy_waffle_ocr
bench restart
```

### Support Channels
- **GitHub Issues**: https://github.com/lato-tech/fuzzy-waffle-ocr/issues
- **Documentation**: Check README.md and USER_JOURNEY.md
- **ERPNext Community**: Post in ERPNext forums with [fuzzy-waffle-ocr] tag

### Health Check Script
```bash
#!/bin/bash
# Save as check_ocr_health.sh

echo "=== Fuzzy Waffle OCR Health Check ==="

# Check tesseract
echo "1. Tesseract Status:"
tesseract --version 2>/dev/null || echo "❌ Tesseract not found"

# Check Python dependencies  
echo "2. Python Dependencies:"
python -c "import pytesseract, PIL, cv2, fuzzywuzzy; print('✅ All OCR dependencies found')" 2>/dev/null || echo "❌ Missing Python dependencies"

# Check app installation
echo "3. App Status:"
bench --site $1 list-apps | grep fuzzy_waffle_ocr && echo "✅ App installed" || echo "❌ App not found"

# Check learning data
echo "4. Learning Data:"
bench --site $1 console -c "import frappe; print('✅ Learning records:', frappe.db.count('Supplier Item Mapping'))"

echo "=== Health Check Complete ==="
```

Usage: `./check_ocr_health.sh your-site-name`

This completes the installation guide. The system should now be ready for intelligent OCR processing with comprehensive learning capabilities!