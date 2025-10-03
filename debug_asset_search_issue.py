from app import create_app
from app.models import Asset, Location

app = create_app()
with app.app_context():
    print("=== ASSET SEARCH ISSUE DEBUG ===")
    
    # Asset ID 147 (Synology) direkt laden
    synology_asset = Asset.query.get(147)
    
    if synology_asset:
        print(f"Synology Asset Details:")
        print(f"  ID: {synology_asset.id}")
        print(f"  Name: '{synology_asset.name}'")
        print(f"  Location (raw): {synology_asset.location}")
        print(f"  Location Object: {synology_asset.location_obj.name if synology_asset.location_obj else 'None'}")
        print(f"  Status: {synology_asset.status}")
        print(f"  Created: {synology_asset.created_at}")
    else:
        print("ERROR: Asset ID 147 not found!")
    
    # Test verschiedene Suchvarianten
    print(f"\n=== TESTING DIFFERENT SEARCH QUERIES ===")
    
    # 1. Alle Assets mit Synology im Namen
    synology_all = Asset.query.filter(Asset.name.ilike('%synology%')).all()
    print(f"1. All assets with 'synology' in name: {len(synology_all)}")
    for asset in synology_all:
        loc_name = asset.location_obj.name if asset.location_obj else f"Location ID {asset.location}"
        print(f"   - {asset.name} (ID: {asset.id}) -> {loc_name}")
    
    # 2. Bielefeld Location
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    if bielefeld:
        print(f"\n2. Bielefeld Location ID: {bielefeld.id}")
        
        # 3. Alle Assets in Bielefeld
        bielefeld_assets = Asset.query.filter_by(location=bielefeld.id).all()
        print(f"3. All assets in Bielefeld: {len(bielefeld_assets)}")
        for asset in bielefeld_assets:
            print(f"   - {asset.name} (ID: {asset.id}) Status: {asset.status}")
        
        # 4. Synology Assets in Bielefeld - verschiedene Varianten
        synology_bielefeld_1 = Asset.query.filter(
            Asset.name.ilike('%synology%'),
            Asset.location == bielefeld.id
        ).all()
        print(f"4. Synology in Bielefeld (method 1): {len(synology_bielefeld_1)}")
        
        synology_bielefeld_2 = Asset.query.filter_by(location=bielefeld.id).filter(
            Asset.name.ilike('%synology%')
        ).all()
        print(f"5. Synology in Bielefeld (method 2): {len(synology_bielefeld_2)}")
    
    # 6. Check Status Filter
    print(f"\n=== STATUS FILTER TEST ===")
    if synology_asset:
        same_status_assets = Asset.query.filter_by(status=synology_asset.status).count()
        print(f"Assets with status '{synology_asset.status}': {same_status_assets}")
        
        # Test if status filter affects search
        synology_active = Asset.query.filter(
            Asset.name.ilike('%synology%'),
            Asset.status == 'active'
        ).all()
        print(f"Synology assets with status 'active': {len(synology_active)}")
    
    # 7. Test MD3 Assets Route Filter Simulation
    print(f"\n=== MD3 ASSETS ROUTE FILTER SIMULATION ===")
    
    # Simulate the MD3 assets route filtering
    query = Asset.query
    
    # Standard filters that might be applied
    query = query.filter(Asset.status == 'active')  # Standard active filter
    
    # Location filter (if Bielefeld is selected)
    if bielefeld:
        query = query.filter(Asset.location == bielefeld.id)
    
    # Name filter (search for Synology)
    query = query.filter(Asset.name.ilike('%synology%'))
    
    filtered_results = query.all()
    print(f"MD3 route simulation results: {len(filtered_results)}")
    
    for asset in filtered_results:
        print(f"   - {asset.name} (ID: {asset.id})")
    
    # 8. Check raw SQL to see what's happening
    print(f"\n=== RAW SQL DEBUG ===")
    if bielefeld and synology_asset:
        # Build the exact query that MD3 assets would use
        from sqlalchemy import text
        
        raw_query = """
        SELECT id, name, location, status 
        FROM asset 
        WHERE name ILIKE :name_pattern 
        AND location = :location_id
        AND status = :status
        """
        
        result = app.db.session.execute(text(raw_query), {
            'name_pattern': '%synology%',
            'location_id': bielefeld.id,
            'status': 'active'
        }).fetchall()
        
        print(f"Raw SQL results: {len(result)}")
        for row in result:
            print(f"   - ID: {row.id}, Name: {row.name}, Location: {row.location}, Status: {row.status}")
    
    # 9. Check if there are any DB commit issues
    print(f"\n=== DB COMMIT STATUS ===")
    from app import db
    print(f"DB session new objects: {len(db.session.new)}")
    print(f"DB session dirty objects: {len(db.session.dirty)}")
    print(f"DB session deleted objects: {len(db.session.deleted)}")
    
    # Manual commit to ensure everything is saved
    try:
        db.session.commit()
        print("Manual DB commit successful")
    except Exception as e:
        print(f"Manual DB commit failed: {e}")
