from app import create_app
from app.models import Asset

app = create_app()

# Test dashboard route direkt
with app.test_client() as client:
    with app.app_context():
        print("=== DASHBOARD ROUTE DEBUG ===")
        
        # Database counts prüfen
        active_count = Asset.query.filter_by(status='active').count()
        on_loan_count = Asset.query.filter_by(status='on_loan').count()
        inactive_count = Asset.query.filter(Asset.status.in_(['inactive', 'defect'])).count()
        total_count = Asset.query.count()
        
        print(f"Database Counts:")
        print(f"  Active: {active_count}")
        print(f"  On Loan: {on_loan_count}")
        print(f"  Inactive: {inactive_count}")
        print(f"  Total: {total_count}")
        
        # Test HTTP Request mit session (um Auth zu umgehen)
        with client.session_transaction() as sess:
            sess['user_id'] = 1  # Mock user login
            sess['user_email'] = 'test@example.com'
            
        response = client.get('/dashboard')
        print(f"Dashboard HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            response_text = response.get_data(as_text=True)
            
            # Suche nach Asset-Zahlen im HTML
            numbers_to_check = [str(active_count), str(total_count)]
            
            for number in numbers_to_check:
                if number in response_text:
                    print(f"Found {number} in HTML")
                else:
                    print(f"Missing {number} in HTML")
                    
            # Prüfe auf hardcoded 0 oder 140
            if '"0"' in response_text:
                print("WARNING: Found hardcoded '0' in HTML")
            if '140' in response_text:
                print("WARNING: Found hardcoded '140' in HTML")
                
        # Test auch MD3 assets route
        print(f"\n=== MD3 ASSETS ROUTE TEST ===")
        response_md3 = client.get('/md3/assets')
        print(f"MD3 Assets HTTP Status: {response_md3.status_code}")
        
        if response_md3.status_code == 200:
            # Check für neue Assets im MD3 HTML
            md3_text = response_md3.get_data(as_text=True)
            test_names = ["Logitech HD-Webcam", "MANHATTAN USB Kabel"]
            
            found_in_md3 = 0
            for name in test_names:
                if name in md3_text:
                    found_in_md3 += 1
                    print(f"Found '{name}' in MD3 assets page")
                else:
                    print(f"Missing '{name}' in MD3 assets page")
                    
            print(f"MD3 Assets Result: {found_in_md3}/{len(test_names)} assets found")
