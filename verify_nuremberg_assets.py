from app import create_app
from app.models import Asset, Location

app = create_app()
with app.app_context():
    # Prüfe die neuen Nürnberg Assets
    nuremberg_location = Location.query.filter(Location.name.ilike('%Nürnberg%')).first()
    
    print("=== VERIFIKATION NÜRNBERG ASSETS ===")
    print(f"Location: {nuremberg_location.name} (ID: {nuremberg_location.id})")
    
    # Alle Assets für Nürnberg
    nuremberg_assets = Asset.query.filter_by(location_id=nuremberg_location.id).all()
    print(f"Gesamte Assets in Nürnberg: {len(nuremberg_assets)}")
    
    for asset in nuremberg_assets:
        print(f"  - ID {asset.id}: {asset.name} (Status: {asset.status})")
    
    # Teste MD3 Assets Route Simulation
    print(f"\n=== MD3 ASSETS ROUTE SIMULATION ===")
    
    # Standard Filter wie in md3_assets Route
    query = Asset.query.filter_by(status='active')
    
    # Location Filter für Nürnberg simulieren
    query_nuremberg = query.join(Asset.location_obj).filter(
        Location.name.ilike('%Nürnberg%')
    )
    
    filtered_assets = query_nuremberg.all()
    print(f"Aktive Assets in Nürnberg (gefiltert): {len(filtered_assets)}")
    
    for asset in filtered_assets:
        print(f"  - ID {asset.id}: {asset.name}")
        
# Test HTTP Request zu MD3 Assets mit Location-Filter
print(f"\n=== HTTP TEST MIT LOCATION FILTER ===")
with app.test_client() as client:
    response = client.get('/md3/assets?location=Nürnberg')
    print(f"HTTP Status: {response.status_code}")
    
    if response.status_code == 200:
        response_text = response.get_data(as_text=True)
        
        # Suche nach den spezifischen Asset-Namen
        test_assets = ["Logitech HD-Webcam C920e black retail", "MANHATTAN USB Kabel A"]
        
        found_count = 0
        for asset_name in test_assets:
            if asset_name in response_text:
                print(f"✓ FOUND: {asset_name}")
                found_count += 1
            else:
                print(f"✗ MISSING: {asset_name}")
                
        print(f"Ergebnis: {found_count}/{len(test_assets)} Assets im HTML gefunden")
    else:
        print(f"Fehler: HTTP {response.status_code}")
