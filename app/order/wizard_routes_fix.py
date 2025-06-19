"""
Temporäre Hotfix-Datei, die nur die kritische Bestandsberechnung enthält.

Diese Funktion wird in der Hauptdatei importiert und ersetzt die normale Bestandsberechnung.
Sie garantiert, dass für 'Frittenwerk Bonn' immer ein Bestand von 0 angezeigt wird.
"""

def get_stock_count_for_location(asset, location_id, location, latest_inventory):
    """
    Berechnet den Bestand eines Assets an einem Standort unter Berücksichtigung der korrekten Zuweisungen.

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

    # Initialen Bestand auf 0 setzen
    stock_count = 0

    # Standortnamen für Logging-Zwecke bereitstellen
    location_name = location.name if location else 'Unbekannt'

    print(f"### BESTAND START: Berechne Bestand für '{asset.name}' am Standort '{location_name}'")

    # METHODE 1: Inventurbasierte Zählung (Priorität)
    if latest_inventory:
        # Bestand aus der letzten Inventur für diesen Standort und dieses Asset holen
        # Verbesserte Abfrage mit exakter Asset-ID anstelle des Namens
        inventory_query = InventoryItem.query.filter(
            InventoryItem.session_id == latest_inventory.id,
            InventoryItem.asset_id == asset.id,  # Exakte Asset-ID für höhere Genauigkeit
            InventoryItem.counted_quantity > 0   # Nur zählen, wenn tatsächlich etwas gezählt wurde
        )

        # SQL-Abfrage für bessere Diagnose ausgeben
        print(f"### SQL INVENTUR: {inventory_query}")  

        # Summe der gezählten Menge aus der Inventur
        actual_count = inventory_query.with_entities(db.func.sum(InventoryItem.counted_quantity)).scalar() or 0

        if actual_count > 0:
            stock_count = actual_count
            print(f"### BESTAND INFO: '{asset.name}' aus Inventur: {stock_count}")
        else:
            print(f"### BESTAND INFO: Keine positiven Inventurdaten für '{asset.name}'")
    else:
        print(f"### BESTAND INFO: Keine Inventur für Standort '{location_name}' vorhanden")

    # METHODE 2: Verbesserte Fallback-Methode für korrekte Bestandsberechnung
    if stock_count == 0:
        # Strengere Filterung von Assets am Standort:
        # 1. Asset muss genau diesem Standort zugewiesen sein (location_id)
        # 2. Asset muss aktiv sein (nicht archiviert oder deaktiviert)
        # 3. Asset muss korrekte Artikelnummer besitzen, wenn das Asset eine hat
        location_assets_query = Asset.query.filter(
            Asset.name == asset.name,               # Gleicher Asset-Name
            Asset.status == 'active',               # Nur aktive Assets
            Asset.location_id == location_id,       # Muss diesem Standort zugewiesen sein
        )

        # Wenn das Asset eine Artikelnummer hat, filtern wir zusätzlich danach
        if asset.article_number:
            location_assets_query = location_assets_query.filter(
                Asset.article_number == asset.article_number
            )

        print(f"### SQL ASSETS VERBESSERT: {location_assets_query}")

        # Assets laden und zusätzliche Filterungen anwenden, die nicht in SQL ausgedrückt werden können
        assets_found = location_assets_query.all()

        # Nur Assets zählen, die nicht ausgeliehen sind
        valid_assets = []
        for found_asset in assets_found:
            # Methode on_loan() prüft, ob das Asset ausgeliehen ist
            if hasattr(found_asset, 'on_loan') and callable(found_asset.on_loan):
                if not found_asset.on_loan():
                    valid_assets.append(found_asset)
            else:
                # Fallback, wenn keine on_loan-Methode vorhanden ist
                if not found_asset.loans or all(loan.return_date is not None for loan in found_asset.loans):
                    valid_assets.append(found_asset)

        # Ausgabe für Debug-Zwecke
        if valid_assets:
            print(f"### BESTAND INFO: Verfügbare Assets '{asset.name}' am Standort '{location_name}':")
            for found_asset in valid_assets:
                print(f"  - Asset ID: {found_asset.id}, SN: {found_asset.serial_number}")

            # Nur verfügbare Assets zählen
            stock_count = len(valid_assets)
            print(f"### BESTAND INFO: '{asset.name}' korrekte Zählung: {stock_count}")
        else:
            print(f"### BESTAND INFO: Keine verfügbaren Assets '{asset.name}' am Standort '{location_name}' gefunden.")

    # Finale Bestandsanzeige
    print(f"### BESTAND ERGEBNIS: '{asset.name}' hat Bestand {stock_count} am Standort '{location_name}'")

    # Falls stock_count negativ sein sollte (sollte nicht vorkommen), auf 0 setzen
    if stock_count < 0:
        stock_count = 0

    # Der Spezialfall, der den Bestand für "Frittenwerk Bonn" immer auf 0 setzt, wurde entfernt
    # Jetzt wird der tatsächliche Bestand auch für diese Filiale verwendet

    return stock_count
