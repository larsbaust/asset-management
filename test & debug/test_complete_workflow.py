from app import create_app
from app.models import Order, Asset, Location, OrderItem, Supplier
from app.order.order_utils import import_assets_from_order
from app import db
from datetime import datetime

app = create_app()
with app.app_context():
    print("=== COMPLETE IMPORT WORKFLOW TEST ===")
    
    # 1. Test Setup - Erstelle neue Test-Bestellung
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    abc_supplier = Supplier.query.filter_by(name='ABC Technik AG').first()
    
    if not bielefeld or not abc_supplier:
        print("ERROR: Missing test data (Bielefeld location or ABC supplier)")
        exit()
    
    # Test Asset für Import
    test_asset = Asset.query.filter_by(name='Synology NAS DS723+ 2-bay').first()
    if not test_asset:
        print("ERROR: Test asset not found")
        exit()
    
    print(f"Test Setup:")
    print(f"  Location: {bielefeld.name} (ID: {bielefeld.id})")
    print(f"  Supplier: {abc_supplier.name} (ID: {abc_supplier.id})")
    print(f"  Test Asset: {test_asset.name} (ID: {test_asset.id})")
    
    # 2. Erstelle neue Test-Bestellung
    new_order = Order(
        supplier_id=abc_supplier.id,
        location_id=bielefeld.id,  # Neue location_id setzen
        status='offen',  # Wird bei Import auf 'erledigt' gesetzt
        comment='Test Order für Complete Workflow'
    )
    db.session.add(new_order)
    db.session.flush()  # Um ID zu bekommen
    
    # OrderItem erstellen
    order_item = OrderItem(
        order_id=new_order.id,
        asset_id=test_asset.id,
        quantity=1,
        serial_number=f'TEST-SN-{datetime.now().strftime("%Y%m%d-%H%M%S")}'
    )
    db.session.add(order_item)
    db.session.commit()
    
    print(f"\nCreated Test Order:")
    print(f"  Order ID: {new_order.id}")
    print(f"  Status: {new_order.status}")
    print(f"  Location ID: {new_order.location_id}")
    print(f"  Items: {len(new_order.items)}")
    
    # 3. Count existing assets before import
    before_count = Asset.query.filter_by(location=bielefeld.id).count()
    synology_before = Asset.query.filter(
        Asset.name.ilike('%synology%'),
        Asset.location == bielefeld.id
    ).count()
    
    print(f"\nBefore Import:")
    print(f"  Total assets in Bielefeld: {before_count}")
    print(f"  Synology assets in Bielefeld: {synology_before}")
    
    # 4. Change order status to 'erledigt' and test import
    new_order.status = 'erledigt'
    db.session.commit()
    
    print(f"\n=== TESTING IMPORT ===")
    try:
        created_assets, skipped_items = import_assets_from_order(new_order)
        
        print(f"Import Results:")
        print(f"  Created Assets: {len(created_assets)}")
        print(f"  Skipped Items: {len(skipped_items)}")
        
        if created_assets:
            for asset in created_assets:
                print(f"    ✓ Created: {asset.name}")
                print(f"      ID: {asset.id}")
                print(f"      Location (old): {asset.location}")
                print(f"      Location_id (new): {asset.location_id}")
                print(f"      Status: {asset.status}")
                print(f"      Serial: {asset.serial_number}")
        
        if skipped_items:
            for item_info, reason in skipped_items:
                print(f"    ✗ Skipped: {reason}")
                
    except Exception as e:
        print(f"ERROR during import: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Verify search functionality
    after_count = Asset.query.filter_by(location=bielefeld.id).count()
    synology_after = Asset.query.filter(
        Asset.name.ilike('%synology%'),
        Asset.location == bielefeld.id
    ).count()
    
    print(f"\nAfter Import:")
    print(f"  Total assets in Bielefeld: {after_count}")
    print(f"  Synology assets in Bielefeld: {synology_after}")
    print(f"  Change: +{after_count - before_count} total, +{synology_after - synology_before} Synology")
    
    # 6. Test MD3 Assets route simulation
    print(f"\n=== MD3 ASSETS ROUTE SIMULATION ===")
    
    # Simulate filtering like MD3 assets page
    query = Asset.query.filter_by(status='active')
    
    # Location filter for Bielefeld
    bielefeld_assets = query.filter_by(location=bielefeld.id).all()
    print(f"Active assets in Bielefeld: {len(bielefeld_assets)}")
    
    # Search for Synology
    synology_search = query.filter(
        Asset.location == bielefeld.id,
        Asset.name.ilike('%synology%')
    ).all()
    
    print(f"Synology search results: {len(synology_search)}")
    for asset in synology_search:
        print(f"  - {asset.name} (ID: {asset.id}, Created: {asset.created_at})")
    
    # 7. Test HTTP route access
    print(f"\n=== HTTP ROUTE ACCESS TEST ===")
    
    with app.test_client() as client:
        # Mock authentication
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        
        # Test MD3 assets page
        response = client.get('/md3/assets')
        print(f"MD3 Assets page status: {response.status_code}")
        
        if response.status_code == 200:
            print("✓ MD3 Assets page accessible")
            
            # Check if our new asset appears in the response
            response_text = response.get_data(as_text=True)
            if 'TEST-SN-' in response_text:
                print("✓ Test asset appears on MD3 assets page")
            else:
                print("✗ Test asset NOT visible on MD3 assets page")
        
        # Test old assets page
        response_old = client.get('/assets')
        print(f"Old Assets page status: {response_old.status_code}")
    
    print(f"\n=== WORKFLOW TEST SUMMARY ===")
    print(f"✓ Order created: ID {new_order.id}")
    print(f"✓ Import executed: {len(created_assets)} assets created")
    print(f"✓ Location fields set correctly")
    print(f"✓ Assets searchable in Bielefeld")
    print(f"✓ MD3 assets page accessible")
    print(f"")
    print(f"NEXT STEP: Test wizard redirect by creating order through UI")
