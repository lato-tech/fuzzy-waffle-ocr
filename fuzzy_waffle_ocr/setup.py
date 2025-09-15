from setuptools import setup, find_packages

with open("requirements.txt") as f:
    install_requires = f.read().strip().split("\n")

# get version from __version__ variable in fuzzy_waffle_ocr/__init__.py
from fuzzy_waffle_ocr import __version__ as version

setup(
    name="fuzzy_waffle_ocr",
    version=version,
    description="Intelligent OCR-based invoice processing for ERPNext with learning capabilities",
    author="Lato Technologies",
    author_email="lato@getlato.com",
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires
)