from app import create_app
from app.models import Asset, Order

app = create_app()
with app.app_context():
    print("=== DASHBOARD COUNT UPDATE TEST ===")
    
    # Aktuelle Counts aus DB
    current_active = Asset.query.filter_by(status='active').count()
    current_total = Asset.query.count()
    
    print(f"Current DB Counts:")
    print(f"  Active Assets: {current_active}")
    print(f"  Total Assets: {current_total}")
    
    # Check neueste Orders
    recent_orders = Order.query.order_by(Order.id.desc()).limit(3).all()
    print(f"\nRecent Orders:")
    for order in recent_orders:
        location_name = order.location_obj.name if order.location_obj else "No Location"
        items_count = len(order.items) if order.items else 0
        print(f"  Order {order.id}: {location_name} - Status: {order.status} - Items: {items_count}")
    
    # Check Assets created today
    from datetime import datetime
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_assets = Asset.query.filter(Asset.created_at >= today_start).all()
    
    print(f"\nAssets created today: {len(today_assets)}")
    for asset in today_assets:
        location_name = asset.location_obj.name if asset.location_obj else "No Location"
        print(f"  ID {asset.id}: {asset.name} - Location: {location_name}")
    
    # Test with mock user session for Dashboard route
    print(f"\n=== TEST DASHBOARD ROUTE WITH AUTH ===")
    
    with app.test_client() as client:
        # Mock login session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['_user_id'] = '1'
            sess['_fresh'] = True
            
        # Test dashboard access  
        response = client.get('/dashboard')
        print(f"Dashboard HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            response_text = response.get_data(as_text=True)
            
            # Check if current counts appear in HTML
            if str(current_active) in response_text:
                print(f"✓ Active count {current_active} found in HTML")
            else:
                print(f"✗ Active count {current_active} NOT found in HTML")
                
            # Check for hardcoded 0 values
            if '<span id="active-count">0</span>' in response_text or '>0<' in response_text:
                print("⚠ WARNING: Found '0' values in HTML - Dashboard may not be updating")
            else:
                print("✓ No hardcoded 0 values detected")
                
        elif response.status_code == 302:
            print("Dashboard still has auth redirect issue")
        else:
            print(f"Unexpected status: {response.status_code}")
            
        # Test MD3 assets page
        response_md3 = client.get('/md3/assets')
        print(f"MD3 Assets HTTP Status: {response_md3.status_code}")
        
        if response_md3.status_code == 200:
            print("✓ MD3 Assets page accessible")
        else:
            print(f"✗ MD3 Assets page error: {response_md3.status_code}")
