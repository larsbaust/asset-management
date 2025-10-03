from app import create_app
from app.models import Order, Asset, Location, OrderItem, Supplier
from app.order.order_utils import import_assets_from_order
from app import db
from datetime import datetime

app = create_app()
with app.app_context():
    print("=== QUANTITY IMPORT TEST ===")
    
    # Setup test data
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    abc_supplier = Supplier.query.filter_by(name='ABC Technik AG').first()
    test_asset = Asset.query.filter_by(name='Synology NAS DS723+ 2-bay').first()
    
    if not all([bielefeld, abc_supplier, test_asset]):
        print("Missing test data")
        exit()
    
    # Count before
    before_count = Asset.query.filter_by(location=bielefeld.id).count()
    print(f"Assets in Bielefeld before test: {before_count}")
    
    # Create test order with quantity > 1
    test_order = Order(
        supplier_id=abc_supplier.id,
        location_id=bielefeld.id,
        status='erledigt',
        comment='Quantity Test Order'
    )
    db.session.add(test_order)
    db.session.flush()
    
    # Create OrderItem with quantity 3
    test_quantity = 3
    order_item = OrderItem(
        order_id=test_order.id,
        asset_id=test_asset.id,
        quantity=test_quantity,
        serial_number=None  # No serial number to test quantity logic
    )
    db.session.add(order_item)
    db.session.commit()
    
    print(f"\nTest Order Created:")
    print(f"  Order ID: {test_order.id}")
    print(f"  Item Quantity: {test_quantity}")
    print(f"  Asset: {test_asset.name}")
    
    # Test import
    print(f"\n=== TESTING IMPORT ===")
    try:
        created_assets, skipped_items = import_assets_from_order(test_order)
        
        print(f"Import Results:")
        print(f"  Created Assets: {len(created_assets)}")
        print(f"  Expected: {test_quantity}")
        print(f"  Match: {'✓' if len(created_assets) == test_quantity else '✗'}")
        
        if created_assets:
            for i, asset in enumerate(created_assets, 1):
                print(f"    {i}. {asset.name} (ID: {asset.id})")
                print(f"       Serial: {asset.serial_number}")
                print(f"       Location: {asset.location}")
        
        if skipped_items:
            print(f"  Skipped Items: {len(skipped_items)}")
            for item_info, reason in skipped_items:
                print(f"    - {item_info}: {reason}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    
    # Verify final count
    after_count = Asset.query.filter_by(location=bielefeld.id).count()
    increase = after_count - before_count
    
    print(f"\nFinal Verification:")
    print(f"  Assets before: {before_count}")
    print(f"  Assets after: {after_count}")
    print(f"  Increase: {increase}")
    print(f"  Expected increase: {test_quantity}")
    print(f"  Correct: {'✓' if increase == test_quantity else '✗'}")
    
    # Cleanup test order
    try:
        db.session.delete(test_order)
        db.session.commit()
        print(f"\nTest order {test_order.id} cleaned up")
    except Exception as e:
        print(f"Cleanup failed: {e}")
