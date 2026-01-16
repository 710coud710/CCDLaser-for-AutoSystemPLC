"""
Template Data Model
Simple template system for CCD image processing with barcode scanning
"""

from .template_model import Template, CropRegion
from .template_service import TemplateService

__all__ = [
    'Template',
    'CropRegion',
    'TemplateService'
]

