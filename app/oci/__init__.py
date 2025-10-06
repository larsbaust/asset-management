"""
OCI (Open Catalog Interface) Integration
Handles B2B procurement with shop.api.de
"""

from .routes import oci_bp
from .service import OCIService

__all__ = ['oci_bp', 'OCIService']
