"""
OCI Service - Business Logic for OCI Integration
"""

from flask import url_for
from typing import Dict, List, Optional
from datetime import datetime
import re

from app.models import Asset, Supplier, AssetSupplierPrice, db
from app.oci.config import OCIConfig


class OCIService:
    """Service for handling OCI operations"""
    
    @staticmethod
    def build_outbound_request(user_id: Optional[str] = None, context: Optional[Dict] = None) -> Dict:
        """
        Build OCI outbound request to open shop.api.de catalog
        
        Args:
            user_id: Optional user identifier
            context: Optional context data (budget, department, etc.)
            
        Returns:
            Dictionary with OCI POST fields
        """
        hook_url = OCIConfig.get_hook_url()
        
        # shop.api.de Feldnamen (aus HTML-Formular extrahiert)
        request_data = {
            'loginId': OCIConfig.SHOP_API_LOGIN_ID,      # Kundennummer (name="loginId")
            'subUserId': OCIConfig.SHOP_API_USERNAME,    # Mitbenutzer (name="subUserId")
            'password': OCIConfig.SHOP_API_PASSWORD,     # Passwort (name="password")
            'HOOK_URL': hook_url                         # OCI Callback URL
        }
        
        # Add context data as custom fields if needed
        if context:
            # Example: pass budget, department, etc.
            pass
        
        return request_data
    
    @staticmethod
    def parse_inbound_response(form_data: Dict) -> List[Dict]:
        """
        Parse OCI inbound response (shopping cart from shop.api.de)
        
        Args:
            form_data: POST form data from shop.api.de
            
        Returns:
            List of items with normalized field names
        """
        items = []
        
        # OCI uses indexed fields: NEW_ITEM-QUANTITY[1], NEW_ITEM-QUANTITY[2], etc.
        # Find all indices
        indices = set()
        for key in form_data.keys():
            match = re.search(r'\[(\d+)\]', key)
            if match:
                indices.add(int(match.group(1)))
        
        # Parse each item
        for index in sorted(indices):
            item = OCIService._parse_single_item(form_data, index)
            if item:
                items.append(item)
        
        return items
    
    @staticmethod
    def _parse_single_item(form_data: Dict, index: int) -> Optional[Dict]:
        """Parse a single OCI item by index"""
        
        def get_field(field_name: str) -> Optional[str]:
            """Get OCI field value by index"""
            key = f"{field_name}[{index}]"
            return form_data.get(key)
        
        # Required fields
        quantity = get_field('NEW_ITEM-QUANTITY')
        if not quantity:
            return None
        
        try:
            # shop.api.de sendet quantity als Float-String (z.B. "1.00")
            quantity_float = float(quantity)
            quantity_int = int(quantity_float)
            
            # shop.api.de verwendet LONGTEXT_0:132[] statt LONGTEXT_1:132[0]
            longtext = form_data.get(f'NEW_ITEM-LONGTEXT_{index}:132[]', '') or get_field('NEW_ITEM-LONGTEXT_1:132') or ''
            
            item = {
                'index': index,
                'quantity': quantity_int,
                'sku': get_field('NEW_ITEM-VENDORMAT') or '',
                'description': get_field('NEW_ITEM-DESCRIPTION') or '',
                'price': float(get_field('NEW_ITEM-PRICE') or 0),
                'currency': get_field('NEW_ITEM-CURRENCY') or 'EUR',
                'unit': get_field('NEW_ITEM-UNIT') or 'ST',
                'vendor': get_field('NEW_ITEM-VENDOR') or 'shop.api.de',
                'matgroup': get_field('NEW_ITEM-MATGROUP') or '',
                'leadtime': int(float(get_field('NEW_ITEM-LEADTIME') or 0)),
                'priceunit': get_field('NEW_ITEM-PRICEUNIT') or '1',
                'vat': get_field('NEW_ITEM-CUST_FIELD1') or '19%',
                'longtext': longtext,
            }
            
            return item
            
        except (ValueError, TypeError) as e:
            print(f"⚠️ Parse-Fehler bei Item {index}: {e}")
            return None
    
    @staticmethod
    def create_or_update_assets_from_oci(items: List[Dict], user_id: int) -> List[Asset]:
        """
        Create or update assets from OCI cart items
        
        Args:
            items: Parsed OCI items
            user_id: User who initiated the OCI request
            
        Returns:
            List of created/updated Asset objects
        """
        assets = []
        
        # Get or create shop.api.de supplier
        supplier = Supplier.query.filter_by(name='shop.api.de').first()
        if not supplier:
            supplier = Supplier(
                name='shop.api.de',
                contact_info='OCI Integration',  # ✅ contact_info statt contact_person
                email='shop@api.de',
                website='https://shop.api.de'
            )
            db.session.add(supplier)
            db.session.flush()
        
        # Get or create "OCI Import" category
        from app.models import Category
        oci_category = Category.query.filter_by(name='OCI Import').first()
        if not oci_category:
            oci_category = Category(name='OCI Import', description='Automatisch importierte Assets aus OCI')
            db.session.add(oci_category)
            db.session.flush()
        
        for item in items:
            # Try to find existing asset by SKU
            asset = Asset.query.filter_by(article_number=item['sku']).first()
            
            if not asset:
                # Create new asset from OCI data
                asset = Asset(
                    name=item['description'],
                    article_number=item['sku'],
                    value=item['price'],
                    category_id=oci_category.id,  # ✅ category_id statt category
                    status='active',  # ✅ 'active' statt 'available'
                    ean=item.get('sku', ''),  # SKU als EAN verwenden
                    description=item.get('longtext', ''),
                    # Add more fields as needed
                )
                db.session.add(asset)
                db.session.flush()
            else:
                # Update existing asset
                asset.value = item['price']
                asset.name = item['description']
                asset.description = item.get('longtext', asset.description)
            
            # Update supplier price
            supplier_price = AssetSupplierPrice.query.filter_by(
                asset_id=asset.id,
                supplier_id=supplier.id
            ).first()
            
            if not supplier_price:
                supplier_price = AssetSupplierPrice(
                    asset_id=asset.id,
                    supplier_id=supplier.id,
                    price=item['price'],
                    currency=item['currency'],
                    supplier_article_number=item['sku'],
                    delivery_time_days=item['leadtime'],
                    payment_terms=f"Lieferzeit: {item['leadtime']} Tage"
                )
                db.session.add(supplier_price)
            else:
                supplier_price.price = item['price']
                supplier_price.delivery_time_days = item['leadtime']
                supplier_price.last_updated = datetime.utcnow()
            
            # Verknüpfe Asset mit Supplier (n:m-Beziehung)
            if supplier not in asset.suppliers:
                asset.suppliers.append(supplier)
            
            assets.append(asset)
        
        db.session.commit()
        return assets
    
    @staticmethod
    def sync_prices_from_oci(items: List[Dict]) -> int:
        """
        Sync prices from OCI cart to AssetSupplierPrice table
        Useful for price comparison without creating orders
        
        Returns:
            Number of prices synced
        """
        synced = 0
        
        supplier = Supplier.query.filter_by(name='shop.api.de').first()
        if not supplier:
            return 0
        
        for item in items:
            # Find asset by SKU
            asset = Asset.query.filter_by(article_number=item['sku']).first()
            if not asset:
                continue
            
            # Update or create price entry
            supplier_price = AssetSupplierPrice.query.filter_by(
                asset_id=asset.id,
                supplier_id=supplier.id
            ).first()
            
            if supplier_price:
                supplier_price.price = item['price']
                supplier_price.last_updated = datetime.utcnow()
                synced += 1
        
        db.session.commit()
        return synced
