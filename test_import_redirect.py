from app import create_app
from app.models import Order, Asset
import requests
from urllib.parse import urlencode

app = create_app()

def test_wizard_import_redirect():
    print("=== WIZARD IMPORT REDIRECT TEST ===")
    
    with app.test_client() as client:
        # Mock login session
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['_user_id'] = '1'
            sess['_fresh'] = True
            
        # Find an order to test import with
        with app.app_context():
            recent_order = Order.query.filter_by(status='offen').first()
            if not recent_order:
                print("No 'offen' order found - creating test scenario")
                return
                
            print(f"Testing with Order ID: {recent_order.id}")
            print(f"Order Location: {recent_order.location_obj.name if recent_order.location_obj else 'No Location'}")
            print(f"Order Items: {len(recent_order.items)}")
            
            # Simulate wizard session data
            with client.session_transaction() as sess:
                sess['wizard_data'] = {
                    'supplier_id': recent_order.supplier_id,
                    'location_id': recent_order.location,
                    'selected_assets': {}
                }
                # Build selected assets from order items
                selected_assets = {}
                for item in recent_order.items:
                    selected_assets[str(item.asset_id)] = {
                        'quantity': item.quantity,
                        'serial_number': item.serial_number or f"SN-{item.id}"
                    }
                sess['wizard_data']['selected_assets'] = selected_assets
                
        print(f"Session setup complete with {len(selected_assets)} assets")
        
        # Test wizard step 4 POST with import action
        form_data = {
            'action': 'import',
            'expected_delivery_date': '2025-08-25',
            'csrf_token': 'test-token'  # In real app this would be generated
        }
        
        print("Sending POST request to wizard step 4...")
        response = client.post('/wizard/step4', 
                             data=form_data, 
                             follow_redirects=False)  # Don't follow to see the redirect
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 302:
            location = response.headers.get('Location')
            print(f"Redirect Location: {location}")
            
            if '/md3/assets' in location:
                print("✓ SUCCESS: Redirects to MD3 Assets page")
                
                # Follow the redirect to test the target page
                follow_response = client.get(location)
                print(f"MD3 Assets page status: {follow_response.status_code}")
                
                if follow_response.status_code == 200:
                    print("✓ SUCCESS: MD3 Assets page loads correctly")
                else:
                    print(f"✗ ERROR: MD3 Assets page returns {follow_response.status_code}")
                    
            elif '/assets' in location and '/md3' not in location:
                print("✗ ERROR: Still redirects to old assets page!")
            else:
                print(f"? UNKNOWN: Redirects to {location}")
        else:
            print("No redirect detected or other response")
            if response.data:
                response_text = response.get_data(as_text=True)[:500]
                print(f"Response content preview: {response_text}")

if __name__ == "__main__":
    test_wizard_import_redirect()
