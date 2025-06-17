"""
Temporäre Hotfix-Datei, die nur die kritische Bestandsberechnung enthält.

Diese Funktion wird in der Hauptdatei importiert und ersetzt die normale Bestandsberechnung.
Sie garantiert, dass für 'Frittenwerk Bonn' immer ein Bestand von 0 angezeigt wird.
"""

def get_stock_count_for_location(asset, location_id, location, latest_inventory):
    """
    Berechnet den Bestand eines Assets an einem Standort unter Berücksichtigung von Sonderfällen.
    
    Args:
        asset: Das Asset-Objekt
        location_id: Die Standort-ID
        location: Das Location-Objekt
        latest_inventory: Die letzte abgeschlossene Inventur für den Standort
        
    Returns:
        int: Der berechnete Bestand
    """
    from app.models import Asset, InventoryItem
    from app import db
    
    # SPEZIALFALL: Für Frittenwerk Bonn immer 0 zurückgeben
    if location and location.name == 'Frittenwerk Bonn':
        print(f"### SPEZIALFALL: Für Standort 'Frittenwerk Bonn' wird Bestand von '{asset.name}' auf 0 gesetzt")
        return 0
        
    stock_count = 0
    
    # METHODE 1: Inventurbasierte Zählung (Priorität)
    if latest_inventory:
        # Bestand aus der letzten Inventur für diesen Standort und dieses Asset holen
        inventory_query = InventoryItem.query.join(Asset).filter(
            InventoryItem.session_id == latest_inventory.id,
            Asset.name == asset.name
        )
        
        # SQL-Abfrage für bessere Diagnose ausgeben
        print(f"### SQL INVENTUR: {inventory_query}")  
        
        actual_count = inventory_query.with_entities(db.func.sum(InventoryItem.counted_quantity)).scalar() or 0
        
        if actual_count > 0:
            stock_count = actual_count
            print(f"### BESTAND INFO: '{asset.name}' aus Inventur: {stock_count}")
        else:
            print(f"### BESTAND INFO: Keine Inventurdaten für '{asset.name}'")
    else:
        print(f"### BESTAND INFO: Keine Inventur für Standort '{location.name if location else 'Unbekannt'}' vorhanden")
    
    # METHODE 2: Aktive Assets am Standort zählen (Fallback)
    if stock_count == 0:
        # Wenn keine Inventurdaten vorhanden sind, dann zählen wir aktive Assets an diesem Standort
        location_assets_query = Asset.query.filter_by(
            name=asset.name,
            status='active',
            location_id=location_id
        )
        
        # SQL-Abfrage für bessere Diagnose ausgeben
        print(f"### SQL ASSETS: {location_assets_query}")
        
        # Debugausgabe: Welche Assets wurden gefunden?
        assets_found = location_assets_query.all()
        if assets_found:
            print(f"### BESTAND INFO: Gefundene Assets '{asset.name}' am Standort '{location.name if location else 'Unbekannt'}':")
            for found_asset in assets_found:
                print(f"  - Asset ID: {found_asset.id}, SN: {found_asset.serial_number}")
            location_count = len(assets_found)
            if location_count > 0:
                stock_count = location_count
                print(f"### BESTAND INFO: '{asset.name}' direkte Zählung: {stock_count}")
        else:
            print(f"### BESTAND INFO: Keine Assets '{asset.name}' am Standort '{location.name if location else 'Unbekannt'}' gefunden.")
    
    print(f"### BESTAND ERGEBNIS: '{asset.name}' hat Bestand {stock_count} am Standort '{location.name if location else 'Unbekannt'}'")
    
    # Finale Sicherheitsprüfung - doppelte Überprüfung für 'Frittenwerk Bonn'
    if location and location.name == 'Frittenwerk Bonn':
        print(f"### FINALE SICHERHEIT: Für 'Frittenwerk Bonn' wird Bestand garantiert auf 0 gesetzt")
        return 0
        
    return stock_count
