from app import create_app
from app.models import Asset

app = create_app()

# Test die Dashboard Route direkt
with app.test_client() as client:
    with app.app_context():
        print("=== FORCING DASHBOARD ROUTE TEST ===")
        
        # Test database counts first
        active_count = Asset.query.filter_by(status='active').count()
        print(f"DB Active count: {active_count}")
        
        # Test HTTP request
        response = client.get('/dashboard')
        print(f"HTTP Status: {response.status_code}")
        
        # Check if debug output appeared in response data
        response_text = response.get_data(as_text=True)
        
        # Look for the asset counts in the response
        if str(active_count) in response_text:
            print(f"✅ Found {active_count} in HTML response")
        else:
            print(f"❌ {active_count} NOT found in HTML response")
            
        # Look for asset_counts template variable usage
        if "asset_counts.active" in response_text:
            print("✅ asset_counts.active found in HTML")
        else:
            print("❌ asset_counts.active NOT found in HTML")
            
        # Look for hardcoded values
        if "'140'" in response_text or '\"140\"' in response_text:
            print("❌ Still has hardcoded 140 value")
        else:
            print("✅ No hardcoded 140 value found")
