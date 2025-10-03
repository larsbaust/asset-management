import requests
from app import create_app
from app.models import Asset

app = create_app()
with app.app_context():
    # Test Database direkt
    print("=== DIREKTE DATABASE ABFRAGE ===")
    active_count = Asset.query.filter_by(status='active').count()
    total_count = Asset.query.count()
    print(f"Aktive Assets: {active_count}")
    print(f"Gesamte Assets: {total_count}")
    
    # Test alle Status-Werte
    all_status = Asset.query.with_entities(Asset.status).distinct().all()
    print(f"\nAlle Status im System:")
    for status in all_status:
        count = Asset.query.filter_by(status=status[0]).count()
        print(f"  '{status[0]}': {count} Assets")

print(f"\n=== HTTP REQUEST TEST ===")
try:
    response = requests.get('http://localhost:5000/dashboard', timeout=5)
    print(f"HTTP Status: {response.status_code}")
    if "135" in response.text:
        print("✅ 135 Assets im HTML gefunden")
    else:
        print("❌ 135 Assets NICHT im HTML gefunden")
        
    # Suche nach asset_counts im HTML
    if "asset_counts" in response.text:
        print("✅ asset_counts Variable im HTML gefunden")
    else:
        print("❌ asset_counts Variable NICHT im HTML gefunden")
        
except Exception as e:
    print(f"HTTP Request Fehler: {e}")
