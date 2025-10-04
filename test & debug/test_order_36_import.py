from app import create_app
from app.models import Order, Asset
from app.order.order_utils import import_assets_from_order

app = create_app()
with app.app_context():
    # Teste Import für Order 36 (Nürnberg)
    order = Order.query.get(36)
    
    if order:
        print(f"=== TESTING IMPORT FOR ORDER {order.id} ===")
        print(f"Location: {order.location_obj.name if order.location_obj else 'None'}")
        print(f"Status: {order.status}")
        print(f"Items: {len(order.items)}")
        
        for item in order.items:
            asset_name = item.asset.name if item.asset else "None"
            print(f"  - Item: {asset_name}, Qty: {item.quantity}, Serial: {item.serial_number}")
        
        # Count assets before import
        before_count = Asset.query.count()
        print(f"Assets before import: {before_count}")
        
        try:
            # Try the import function
            created_assets, skipped_items = import_assets_from_order(order)
            
            print(f"Import result:")
            print(f"  Created assets: {len(created_assets)}")
            print(f"  Skipped items: {len(skipped_items)}")
            
            for asset in created_assets:
                print(f"    Created: ID {asset.id} - {asset.name}")
            
            for skipped in skipped_items:
                print(f"    Skipped: {skipped}")
                
            # Count assets after import
            after_count = Asset.query.count()
            print(f"Assets after import: {after_count}")
            
        except Exception as e:
            print(f"ERROR during import: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("Order 36 not found!")
        
    # Also check the most recent Nürnberg order
    print(f"\n=== CHECKING RECENT NÜRNBERG ORDERS ===")
    recent_nuremberg_orders = Order.query.join(Order.location_obj).filter(
        Order.location_obj.has(name='Frittenwerk Nürnberg')
    ).order_by(Order.id.desc()).limit(2).all()
    
    for order in recent_nuremberg_orders:
        print(f"Order {order.id}: Status={order.status}, Items={len(order.items)}")
