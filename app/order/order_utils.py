from app.models import Asset, asset_suppliers
from app import db
from flask import flash
import logging

# Logger konfigurieren
logger = logging.getLogger(__name__)

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
    
    # Log Start des Import-Prozesses
    logger.info(f"Starte Asset-Import aus Bestellung #{order.id} mit {len(order.items)} Positionen")
    
    for item in order.items:
        serial_number = (item.serial_number or '').strip() if hasattr(item, 'serial_number') else ''
        # Debug-Info zum OrderItem
        quantity = item.quantity if hasattr(item, 'quantity') and item.quantity else 1
        logger.info(f"Verarbeite OrderItem {item.id}, Asset_ID: {item.asset_id if hasattr(item, 'asset_id') else 'N/A'}, Menge: {quantity}")
        
        # Duplikatsprüfung nur bei Seriennummer - aber nicht das ganze Item überspringen
        # wenn Duplikat gefunden wird, da wir trotzdem mehrere Assets für quantity > 1 erstellen müssen
        skip_due_to_duplicate = False
        if serial_number:
            existing_asset = Asset.query.filter_by(serial_number=serial_number).first()
            
            if existing_asset:
                logger.info(f"Asset mit Seriennummer {serial_number} existiert bereits (ID: {existing_asset.id})")
                skipped_items.append((f"{item.asset.name if item.asset else 'Unknown'} (SN: {serial_number})", "Seriennummer bereits vorhanden"))
                skip_due_to_duplicate = True
        
        # Wenn Duplikat gefunden wurde, dieses Item überspringen
        if skip_due_to_duplicate:
            continue

        # Gemeinsame Felder übernehmen
        asset_data = {}
        # Erweiterte Felder-Liste mit allen wichtigen Attributen
        copy_fields = [
            'name', 'category_id', 'manufacturer_id', 'ean', 'article_number', 'serial_number', 
            'comment', 'image_url', 'value', 'status'
        ]
        
        # Referenz-Asset (Template) abrufen
        template_asset = None
        if hasattr(item, 'asset_id') and item.asset_id:
            template_asset = Asset.query.get(item.asset_id)
            logger.info(f"Template-Asset gefunden: ID {template_asset.id if template_asset else 'N/A'}")
        
        # Asset-Daten sammeln, entweder von OrderItem oder von Template-Asset
        for field in copy_fields:
            # Zuerst versuchen, den Wert direkt vom OrderItem zu nehmen
            value = getattr(item, field, None)
            
            # Wenn nicht erfolgreich und ein Template-Asset vorhanden ist,
            # dann den Wert vom Template-Asset nehmen
            if (not value or value == '') and template_asset:
                value = getattr(template_asset, field, None)
                
            if value not in [None, '']:
                asset_data[field] = value
        
        # Status IMMER explizit auf 'active' setzen, unabhängig von Vorlage-Asset
        # Dies überschreibt jeden anderen Status, der bereits gesetzt sein könnte
        asset_data['status'] = 'active'  # Erzwinge Status 'active'
        logger.info("Asset-Status wird auf 'active' gesetzt")
        
        # Standort explizit aus der Bestellung übernehmen
        # Damit überschreiben wir einen eventuell vom Template-Asset übernommenen Standort
        if hasattr(order, 'location_id') and order.location_id:
            asset_data['location_id'] = order.location_id
            asset_data['location'] = order.location_id  # Auch das alte location-Feld setzen für Kompatibilität
            logger.info(f"Standort aus Bestellung übernommen: location_id = {order.location_id}")
        else:
            logger.warning(f"Keine location_id in der Bestellung gefunden!")
            # Wenn kein Standort in der Bestellung, dann vom Template-Asset übernehmen
            if template_asset and hasattr(template_asset, 'location_id') and template_asset.location_id:
                asset_data['location_id'] = template_asset.location_id
                asset_data['location'] = template_asset.location_id  # Auch das alte location-Feld setzen
                logger.info(f"Standort vom Template-Asset übernommen: location_id = {template_asset.location_id}")
        
        # Prüfen, ob Name gesetzt ist
        asset_name = asset_data.get('name', None)
        if asset_name and str(asset_name).strip():
            # Menge aus dem Order-Item auslesen und sicherstellen, dass es eine positive Zahl ist
            quantity = 1  # Standard: Ein Asset erstellen
            if hasattr(item, 'quantity') and item.quantity and isinstance(item.quantity, (int, float)) and item.quantity > 0:
                quantity = int(item.quantity)
            
            logger.info(f"Erstelle {quantity} Assets für Position {item.id}")
            
            # Seriennummer nur für das erste Asset verwenden, wenn mehrere Assets erstellt werden
            original_serial = asset_data.get('serial_number', '')
            
            # Für jedes Stück in der Menge ein eigenes Asset anlegen
            for i in range(quantity):
                # Bei mehr als einem Asset und wenn eine Seriennummer vorhanden ist:
                # Für weitere Assets nur die ersten 10 Zeichen der Seriennummer verwenden und Suffix anhängen
                if i > 0 and original_serial:
                    # Neue Seriennummer generieren: Erste 10 Zeichen + Laufnummer
                    prefix = original_serial[:10] if len(original_serial) > 10 else original_serial
                    asset_data['serial_number'] = f"{prefix}-{i+1}"
                    logger.info(f"Generiere neue Seriennummer für zusätzliches Asset: {asset_data['serial_number']}")
                
                # WICHTIG: Status IMMER explizit setzen
                asset_data['status'] = 'active'  # Erzwinge Status 'active'
                
                # Neues Asset erstellen
                new_asset = Asset(**asset_data)
                
                # Direkt nach der Erstellung sicherstellen, dass der Status korrekt ist
                new_asset.status = 'active'  # Zweite Sicherheitsebene
                
                # Asset zur Session hinzufügen
                db.session.add(new_asset)
                
                # Sofort einen Flush durchführen, damit die ID verfügbar ist
                db.session.flush()
                
                logger.info(f"Neues Asset erstellt ({i+1} von {quantity}): ID={new_asset.id}, Name={asset_name}, Status={new_asset.status}")
                
                # Lieferanten-Verknüpfung hinzufügen
                if order.supplier_id:
                    try:
                        # Direktes SQL-Statement vermeiden - stattdessen ORM-Beziehung verwenden
                        from app.models import Supplier
                        supplier = Supplier.query.get(order.supplier_id)
                        if supplier:
                            if not hasattr(new_asset, 'suppliers'):
                                new_asset.suppliers = []
                            new_asset.suppliers.append(supplier)
                            logger.info(f"Lieferant {supplier.name} (ID: {supplier.id}) zum Asset hinzugefügt")
                        else:
                            logger.warning(f"Lieferant mit ID {order.supplier_id} nicht gefunden")
                    except Exception as e:
                        logger.error(f"Fehler beim Hinzufügen des Lieferanten: {e}")
                
                # Zur Liste der erstellten Assets hinzufügen
                created_assets.append(new_asset)
        else:
            logger.warning(f"Asset übersprungen, da kein Name gesetzt: {asset_data}")
            skipped_items.append(item)
    
    # Überprüfung vor dem Commit - sicherstellen, dass alle Assets den richtigen Status haben
    for asset in created_assets:
        if asset.status != 'active':
            logger.warning(f"Asset ID {asset.id} hat falschen Status: {asset.status} - korrigiere zu 'active'")
            asset.status = 'active'
    
    # Änderungen speichern
    try:
        # Commit durchführen
        db.session.commit()
        
        # Erfolgreiches Logging
        if created_assets:
            logger.info(f"Asset-Import erfolgreich: {len(created_assets)} Assets erstellt und gespeichert")
            # Zur Sicherheit alle Assets nochmal loggen
            for asset in created_assets:
                logger.info(f"Gespeichertes Asset: ID={asset.id}, Name={asset.name}, Status={asset.status}, Standort={asset.location_id}")
        else:
            logger.info("Keine neuen Assets erstellt.")
            
        if skipped_items:
            logger.info(f"{len(skipped_items)} Positionen wurden übersprungen")
    except Exception as e:
        # Rollback im Fehlerfall
        db.session.rollback()
        logger.error(f"Fehler beim Speichern der neuen Assets: {str(e)}")
        flash(f"Fehler beim Import der Assets: {str(e)}", 'danger')
        return [], skipped_items
    
    # Feedback-Nachrichten erstellen
    if created_assets:
        msg = f'{len(created_assets)} neue Assets wurden automatisch aus der Bestellung angelegt.'
    else:
        msg = ''
        
    if skipped_items:
        if len(skipped_items) == 1:
            msg += f' 1 Position wurde übersprungen.'
        else:
            msg += f' {len(skipped_items)} Positionen wurden übersprungen.'
    
    if msg:
        try:
            from flask import has_request_context
            if has_request_context():
                flash(msg.strip(), 'warning' if skipped_items else 'success')
            else:
                print(f"Import message: {msg.strip()}")
        except Exception as e:
            print(f"Import message (flash failed): {msg.strip()}")
    
    return created_assets, skipped_items
