# Inventory module for MD3 UX migration
# This module contains all inventory-related routes and functionality for the new MD3 interface

from flask import Blueprint

# Create the inventory blueprint
inventory_bp = Blueprint('md3_inventory', __name__, url_prefix='/md3/inventory')

# Import routes after blueprint creation to avoid circular imports
from . import md3_routes
