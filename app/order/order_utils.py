from app.models import Asset
from app import db
from flask import flash

def import_assets_from_order(order):
    """
    Importiert Assets aus einer Bestellung mit Status 'erledigt'.
    
    Diese Funktion prüft die OrderItems und erstellt neue Assets, wenn keine
    identischen Assets (mit gleicher Seriennummer) existieren.
    
    Parameter:
        order: Order-Objekt mit Status 'erledigt'
    
    Returns:
        tuple: (created_assets, skipped_items) - Listen mit erstellten Assets und übersprungenen Items
    """
    created_assets = []
    skipped_items = []
    
    for item in order.items:
        serial_number = (item.serial_number or '').strip() if hasattr(item, 'serial_number') else ''
        # Prüfen, ob Asset mit dieser Seriennummer existiert
        asset_exists = False
        if serial_number:
            asset_exists = Asset.query.filter_by(serial_number=serial_number).first() is not None
        
        if not asset_exists:
            # Gemeinsame Felder übernehmen
            asset_data = {}
            for field in ['name', 'category_id', 'manufacturer_id', 'ean', 'serial_number', 'comment']:
                # Feld im OrderItem, sonst aus Asset übernehmen
                value = getattr(item, field, None)
                if not value and hasattr(item, 'asset') and item.asset is not None:
                    # Mapping: OrderItem.name -> item.asset.name usw.
                    if field == 'name':
                        value = getattr(item.asset, 'name', None)
                    elif field == 'category_id':
                        value = getattr(item.asset, 'category_id', None)
                    elif field == 'manufacturer_id':
                        value = getattr(item.asset, 'manufacturer_id', None)
                    elif field == 'ean':
                        value = getattr(item.asset, 'ean', None)
                if value:
                    asset_data[field] = value
            
            # Standort korrekt setzen (location_id bevorzugen, fallback auf location-String)
            if hasattr(order, 'location_id') and order.location_id:
                asset_data['location_id'] = order.location_id
            elif hasattr(order, 'location'):
                asset_data['location'] = order.location
            else:
                asset_data['location_id'] = None
            
            # Prüfen, ob Name gesetzt ist (direkt oder über Asset)
            asset_name = asset_data.get('name', None)
            if asset_name and str(asset_name).strip():
                new_asset = Asset(**asset_data)
                db.session.add(new_asset)
                created_assets.append(new_asset)
            else:
                skipped_items.append(item)
    
    # Änderungen speichern
    db.session.commit()
    
    # Feedback-Nachrichten erstellen
    msg = f'{len(created_assets)} neue Assets wurden automatisch aus der Bestellung angelegt.' if created_assets else ''
    if skipped_items:
        msg += f' {len(skipped_items)} Position(en) wurden übersprungen, da kein Name gesetzt war.'
    
    if msg:
        flash(msg.strip(), 'warning' if skipped_items else 'success')
    
    return created_assets, skipped_items
