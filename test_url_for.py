from app import create_app
from flask import url_for

app = create_app()
with app.test_client() as client:
    with app.app_context():
        print("=== URL_FOR ROUTE TESTING ===")
        
        # Test verschiedene url_for Varianten
        try:
            url1 = url_for('md3_assets')
            print(f"url_for('md3_assets'): {url1}")
        except Exception as e:
            print(f"ERROR url_for('md3_assets'): {e}")
            
        try:
            url2 = url_for('main.md3_assets')
            print(f"url_for('main.md3_assets'): {url2}")
        except Exception as e:
            print(f"ERROR url_for('main.md3_assets'): {e}")
            
        # Test direct URL
        try:
            response = client.get('/md3/assets')
            print(f"Direct GET /md3/assets: HTTP {response.status_code}")
        except Exception as e:
            print(f"ERROR direct GET: {e}")
            
        # List all available routes
        print(f"\n=== ALL ROUTES WITH 'assets' ===")
        for rule in app.url_map.iter_rules():
            if 'assets' in rule.rule.lower():
                print(f"Route: {rule.rule} -> {rule.endpoint}")
                
        # Test old assets route
        try:
            response_old = client.get('/assets')
            print(f"Old /assets route: HTTP {response_old.status_code}")
        except Exception as e:
            print(f"ERROR old assets route: {e}")
