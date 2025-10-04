from app import create_app
from app.models import Asset

app = create_app()
with app.app_context():
    # Neue Assets prüfen (heute erstellt) 
    recent_assets = Asset.query.filter(Asset.created_at >= '2025-08-22').order_by(Asset.created_at.desc()).all()
    print(f'=== NEUE ASSETS (heute erstellt): {len(recent_assets)} ===')
    for asset in recent_assets:
        print(f'ID: {asset.id} | Name: {asset.name} | Status: "{asset.status}" | Location: {asset.location_id} | Created: {asset.created_at}')
    
    print(f'\n=== FILTER TEST (status=active) ===')
    active_assets = Asset.query.filter_by(status='active').all()
    print(f'Aktive Assets gesamt: {len(active_assets)}')
    
    print(f'\n=== ALLE STATUS-WERTE ===')
    all_status = Asset.query.with_entities(Asset.status).distinct().all()
    for status in all_status:
        count = Asset.query.filter_by(status=status[0]).count()
        print(f'Status "{status[0]}": {count} Assets')
        
    print(f'\n=== MD3 ASSETS ROUTE SIMULATION ===')
    # Standard Filter wie in md3_assets route
    status = 'active'  # Default
    query = Asset.query
    if status != 'all':
        query = query.filter(Asset.status == status)
    
    filtered_assets = query.all()
    print(f'Assets mit Filter status="{status}": {len(filtered_assets)}')
    
    # Check ob neue Assets in filtered results sind
    new_asset_ids = [a.id for a in recent_assets]
    filtered_new = [a for a in filtered_assets if a.id in new_asset_ids]
    print(f'Neue Assets in gefilterten Ergebnissen: {len(filtered_new)}')
    for asset in filtered_new:
        print(f'  - ID {asset.id}: {asset.name} (Status: {asset.status})')

    # Überprüfen der letzten importierten Assets mit Location
    print('\n=== LETZTE 5 ASSETS MIT LOCATION ===')
    from app.models import Location
    last_assets = Asset.query.order_by(Asset.id.desc()).limit(5).all()
    for asset in last_assets:
        location_name = asset.location_obj.name if asset.location_obj else "Keine Location"
        print(f'ID: {asset.id}, Name: {asset.name}, Status: {asset.status}, Location: {location_name} (ID: {asset.location_id})')
    
    # Teste Location Filter Problem
    print('\n=== LOCATION FILTER TEST ===')
    # Simuliere md3_assets route mit location filter
    query = Asset.query.filter_by(status='active')
    
    # Test: Alle Locations der neuen Assets
    for asset in recent_assets:
        if asset.location_obj:
            print(f'Asset {asset.id} Location: "{asset.location_obj.name}" (ID: {asset.location_id})')
        else:
            print(f'Asset {asset.id} hat KEINE Location! (location_id: {asset.location_id})')
            
    # Test SQL Query wie in Route
    print('\n=== DIREKTE SQL TESTS ===')
    all_locations = Location.query.all()
    print(f'Alle Locations: {len(all_locations)}')
    for loc in all_locations[:3]:
        print(f'  Location ID {loc.id}: "{loc.name}"')
        activated_count = 0
        
        for asset in inactive_assets:
            asset.status = 'active'
            activated_count += 1
        
        db.session.commit()
        print(f'{activated_count} Assets wurden auf "active" gesetzt.')
        
        # Status-Verteilung nach dem Update anzeigen
        print('\nNeue Status-Verteilung:')
        for status in db.session.query(Asset.status).distinct().all():
            count = Asset.query.filter_by(status=status[0]).count()
            print(f'- {status[0]}: {count} Assets')
