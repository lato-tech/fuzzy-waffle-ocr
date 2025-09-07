from setuptools import setup, find_packages

setup(
    name='fuzzy_waffle_ocr',
    version='1.0.0',
    description='Intelligent OCR-based invoice processing for ERPNext with learning capabilities',
    author='Lato Tech',
    author_email='info@namiex.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        'frappe',
        'pytesseract',
        'Pillow',
        'opencv-python',
        'fuzzywuzzy',
        'python-Levenshtein',
        'pdf2image',
        'numpy'
    ],
)