"""
OCI Configuration for shop.api.de
"""

import os
from flask import current_app

class OCIConfig:
    """Configuration for OCI integration with shop.api.de"""
    
    # shop.api.de OCI Credentials (from environment variables)
    SHOP_API_URL = 'https://shop.api.de/login?subUserLogin=1'  # SubUser-Login aktiviert
    SHOP_API_LOGIN_ID = os.getenv('OCI_SHOP_API_LOGIN_ID', '204927')
    SHOP_API_USERNAME = os.getenv('OCI_SHOP_API_USERNAME', 'Lars_Baust')  # Mitbenutzer (subUser)
    SHOP_API_PASSWORD = os.getenv('OCI_SHOP_API_PASSWORD', 'Vonh3rz3n!')
    
    # OCI Field Mappings (extracted from shop.api.de HTML form)
    OCI_OUTBOUND_FIELDS = {
        'loginId': 'loginId',           # Kundennummer (name="loginId" in form)
        'subUserId': 'subUserId',       # Mitbenutzer (name="subUserId" in form)
        'password': 'password',         # Passwort (name="password" in form)
        'HOOK_URL': 'HOOK_URL'          # OCI Callback URL
    }
    
    OCI_INBOUND_FIELDS = {
        'quantity': 'NEW_ITEM-QUANTITY',        # Anzahl des Produktes
        'sku': 'NEW_ITEM-VENDORMAT',           # SKU
        'description': 'NEW_ITEM-DESCRIPTION',  # Titel
        'price': 'NEW_ITEM-PRICE',             # Preis
        'currency': 'NEW_ITEM-CURRENCY',        # Währung (EUR)
        'unit': 'NEW_ITEM-UNIT',               # Mengeneinheit
        'vendor': 'NEW_ITEM-VENDOR',           # SRM - Lieferantennummer
        'matgroup': 'NEW_ITEM-MATGROUP',       # SRM - Warengruppe
        'leadtime': 'NEW_ITEM-LEADTIME',       # Lieferzeit
        'priceunit': 'NEW_ITEM-PRICEUNIT',     # Preiseinheit (1)
        'vat': 'NEW_ITEM-CUST_FIELD1',         # Mehrwertsteuer (19%)
        'longtext': 'NEW_ITEM-LONGTEXT_1:132'  # Beschreibung
    }
    
    @staticmethod
    def get_hook_url():
        """Generate the HOOK_URL for OCI inbound callback"""
        # In production: use actual domain
        # For development: use ngrok or localhost with port forwarding
        base_url = os.getenv('APP_BASE_URL', 'http://127.0.0.1:5000')
        return f"{base_url}/oci/inbound"
    
    @staticmethod
    def get_outbound_url():
        """Get the shop.api.de OCI catalog URL"""
        return OCIConfig.SHOP_API_URL
