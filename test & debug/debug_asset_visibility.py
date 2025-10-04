from app import create_app
from app.models import Asset, Location
from datetime import datetime

app = create_app()
with app.app_context():
    print("=== ASSET VISIBILITY DEBUG ===")
    
    # Check recent assets in Bielefeld
    bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
    if not bielefeld:
        print("Bielefeld not found")
        exit()
    
    print(f"Bielefeld Location ID: {bielefeld.id}")
    
    # All assets in Bielefeld
    all_bielefeld = Asset.query.filter_by(location=bielefeld.id).all()
    print(f"\nTotal assets in Bielefeld: {len(all_bielefeld)}")
    
    # Today's assets
    today = datetime.now().date()
    today_assets = [a for a in all_bielefeld if a.created_at and a.created_at.date() == today]
    print(f"Assets created today: {len(today_assets)}")
    
    for asset in today_assets:
        print(f"  - ID {asset.id}: {asset.name}")
        print(f"    Location: {asset.location} (should be {bielefeld.id})")
        print(f"    Status: {asset.status}")
        print(f"    Created: {asset.created_at}")
    
    # Test MD3 Assets route query simulation
    print(f"\n=== MD3 ASSETS ROUTE SIMULATION ===")
    
    # Simulate the exact query used by MD3 assets route
    query = Asset.query
    
    # Apply filters like in MD3 route
    query = query.filter(Asset.status == 'active')  # Active filter
    query = query.filter(Asset.location == bielefeld.id)  # Location filter
    
    filtered_results = query.all()
    print(f"MD3 route filtered results: {len(filtered_results)}")
    
    # Check what's different
    missing_assets = []
    for asset in today_assets:
        if asset not in filtered_results:
            missing_assets.append(asset)
            print(f"  Missing from MD3 results: {asset.name} (Status: {asset.status}, Location: {asset.location})")
    
    if not missing_assets:
        print("  All today's assets appear in MD3 filtered results")
    
    # Test HTTP response
    print(f"\n=== HTTP RESPONSE TEST ===")
    
    with app.test_client() as client:
        # Mock auth
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['_user_id'] = '1'
            sess['_fresh'] = True
        
        # Test MD3 assets page with Bielefeld filter
        response = client.get(f'/md3/assets?location={bielefeld.id}')
        print(f"HTTP Response: {response.status_code}")
        
        if response.status_code == 200:
            content = response.get_data(as_text=True)
            
            # Count how many of today's assets appear in HTML
            found_count = 0
            for asset in today_assets:
                if asset.name in content:
                    found_count += 1
                    print(f"  ✓ Found in HTML: {asset.name}")
                else:
                    print(f"  ✗ Missing from HTML: {asset.name}")
            
            print(f"\nHTML Visibility Summary:")
            print(f"  Today's assets: {len(today_assets)}")
            print(f"  Found in HTML: {found_count}")
            print(f"  Missing: {len(today_assets) - found_count}")
            
            # Check table structure
            asset_rows = content.count('<tr class="asset-row')
            if asset_rows == 0:
                asset_rows = content.count('<tr data-asset-id')  # Alternative pattern
            
            print(f"  HTML asset rows detected: {asset_rows}")
            
            # Debug HTML structure
            if 'Keine Assets gefunden' in content or 'No assets found' in content:
                print("  HTML shows 'No assets found' message")
            
            # Check JavaScript filters
            if 'filterAssets' in content:
                print("  JavaScript filtering detected")
                
    # Test with different status values
    print(f"\n=== STATUS DEBUG ===")
    status_counts = {}
    for asset in all_bielefeld:
        status = asset.status or 'None'
        status_counts[status] = status_counts.get(status, 0) + 1
    
    print(f"Status distribution in Bielefeld:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")
    
    # Check if there are any status issues
    for asset in today_assets:
        if asset.status != 'active':
            print(f"  WARNING: {asset.name} has status '{asset.status}', not 'active'")
