from app import create_app
from app.models import Asset, Location

app = create_app()

with app.test_client() as client:
    with app.app_context():
        print("=== MD3 ASSETS ROUTE TEST ===")
        
        # Test direkte Database-Abfrage für Assets mit Dresden Location
        dresden_assets = Asset.query.join(Asset.location_obj).filter(
            Location.name.ilike('%Dresden%'),
            Asset.status == 'active'
        ).all()
        
        print(f"Assets in Dresden (DB): {len(dresden_assets)}")
        for asset in dresden_assets[-3:]:  # Letzte 3 Assets
            print(f"  - ID {asset.id}: {asset.name} (Status: {asset.status})")
        
        # Test HTTP Request zu MD3 Assets
        response = client.get('/md3/assets')
        print(f"MD3 Assets HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            response_text = response.get_data(as_text=True)
            
            # Suche nach den neuen Asset-Namen in der HTML Response
            new_assets = ["Brother Trommeleinheit DR-2510", "AVM FRITZ!Box 6850 LTE"]
            
            found_assets = []
            for asset_name in new_assets:
                if asset_name in response_text:
                    found_assets.append(asset_name)
                    print(f"FOUND: {asset_name} in HTML")
                else:
                    print(f"MISSING: {asset_name} not in HTML")
            
            print(f"Summary: {len(found_assets)}/{len(new_assets)} new assets found in HTML")
            
        elif response.status_code == 302:
            print("MD3 Assets has authentication redirect")
        else:
            print(f"Unexpected status code: {response.status_code}")
