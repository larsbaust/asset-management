from app import create_app
from app.models import Asset, Location
from app import db

app = create_app()
with app.app_context():
    print("=== FIX EXISTING SYNOLOGY ASSET ===")
    
    # Asset ID 147 (Synology) direkt laden und location-Feld korrigieren
    synology_asset = Asset.query.get(147)
    
    if synology_asset:
        print(f"Before fix:")
        print(f"  ID: {synology_asset.id}")
        print(f"  Name: {synology_asset.name}")
        print(f"  Location (old): {synology_asset.location}")
        print(f"  Location_id (new): {synology_asset.location_id}")
        
        # location-Feld basierend auf location_id setzen
        if synology_asset.location_id and not synology_asset.location:
            synology_asset.location = synology_asset.location_id
            db.session.commit()
            print(f"  Fixed: location field set to {synology_asset.location}")
        
        print(f"\nAfter fix:")
        print(f"  Location (old): {synology_asset.location}")
        print(f"  Location_id (new): {synology_asset.location_id}")
        
        # Test search nach der Korrektur
        bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
        if bielefeld:
            synology_search = Asset.query.filter(
                Asset.name.ilike('%synology%'),
                Asset.location == bielefeld.id
            ).all()
            
            print(f"\nSearch test after fix:")
            print(f"  Synology assets in Bielefeld: {len(synology_search)}")
            for asset in synology_search:
                print(f"    - {asset.name} (ID: {asset.id})")
    else:
        print("Asset ID 147 not found!")
    
    # Test new import for verification
    print(f"\n=== TEST NEW IMPORT WITH FIXED FUNCTION ===")
    
    # Find Order 39 and test re-import (should skip existing)
    from app.models import Order
    from app.order.order_utils import import_assets_from_order
    
    order = Order.query.get(39)
    if order:
        created_assets, skipped_items = import_assets_from_order(order)
        
        print(f"Test import results:")
        print(f"  Created: {len(created_assets)}")
        print(f"  Skipped: {len(skipped_items)}")
        
        if created_assets:
            for asset in created_assets:
                print(f"    New asset: {asset.name} - Location: {asset.location}/{asset.location_id}")
    
    print(f"\n=== FINAL SEARCH VERIFICATION ===")
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    if bielefeld:
        all_bielefeld_assets = Asset.query.filter_by(location=bielefeld.id).all()
        synology_bielefeld = Asset.query.filter(
            Asset.name.ilike('%synology%'),
            Asset.location == bielefeld.id
        ).all()
        
        print(f"Final results:")
        print(f"  Total assets in Bielefeld: {len(all_bielefeld_assets)}")
        print(f"  Synology assets in Bielefeld: {len(synology_bielefeld)}")
        
        for asset in synology_bielefeld:
            print(f"    - {asset.name} (ID: {asset.id}, Status: {asset.status})")
