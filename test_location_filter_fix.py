#!/usr/bin/env python3
"""
Test Location Filter Fix - Verifiziert ob Dashboard korrekte Asset-Counts zeigt
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Asset, Location
from datetime import datetime

def test_location_filter_fix():
    app = create_app()
    
    with app.app_context():
        print("=== LOCATION FILTER FIX TEST ===")
        
        # 1. Frittenwerk Bielefeld spezifisch testen
        bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
        if not bielefeld:
            print("[ERROR] Frittenwerk Bielefeld nicht gefunden!")
            return
            
        print(f"[OK] Frittenwerk Bielefeld ID: {bielefeld.id}")
        
        # 2. Asset-Counts vergleichen: Alt vs Neu
        old_method_count = Asset.query.filter_by(location='Frittenwerk Bielefeld', status='active').count()
        new_method_count = Asset.query.filter_by(location_id=bielefeld.id, status='active').count()
        
        print(f"\n=== ASSET COUNT VERGLEICH ===")
        print(f"[OLD] Alte Methode (location field): {old_method_count}")
        print(f"[NEW] Neue Methode (location_id): {new_method_count}")
        
        if new_method_count > old_method_count:
            print(f"[SUCCESS] FIX ERFOLGREICH! Dashboard sollte jetzt {new_method_count} statt {old_method_count} anzeigen")
        elif new_method_count == old_method_count and new_method_count > 0:
            print(f"[OK] Beide Methoden zeigen gleiche Werte: {new_method_count}")
        else:
            print(f"[ERROR] Problem: Neue Methode zeigt {new_method_count}, alte {old_method_count}")
        
        # 3. Assets heute erstellt
        today = datetime.now().date()
        assets_today = Asset.query.filter_by(location_id=bielefeld.id, status='active').filter(
            Asset.created_at >= datetime.combine(today, datetime.min.time())
        ).all()
        
        print(f"\n=== HEUTE ERSTELLTE ASSETS ===")
        print(f"[TODAY] Assets erstellt heute ({today}): {len(assets_today)}")
        
        if assets_today:
            print("Details der heutigen Assets:")
            for asset in assets_today:
                print(f"  [ASSET] {asset.name} (ID: {asset.id}) - {asset.created_at}")
        
        # 4. Teste Dashboard-Simulierung
        print(f"\n=== DASHBOARD SIMULATION ===")
        total_active = Asset.query.filter_by(status='active').count()
        total_on_loan = Asset.query.filter_by(status='on_loan').count()
        total_inactive = Asset.query.filter(Asset.status.in_(['inactive', 'defect'])).count()
        
        print(f"[DASHBOARD] Dashboard Counts:")
        print(f"  - Aktiv: {total_active}")
        print(f"  - Ausgeliehen: {total_on_loan}")
        print(f"  - Inaktiv: {total_inactive}")
        
        # 5. Locations mit Asset-Counts
        print(f"\n=== ALLE LOCATIONS MIT ASSET COUNTS ===")
        locations_with_assets = db.session.query(
            Location.name, 
            db.func.count(Asset.id).label('asset_count')
        ).outerjoin(Asset, Location.id == Asset.location_id).filter(
            Asset.status == 'active'
        ).group_by(Location.id, Location.name).having(
            db.func.count(Asset.id) > 0
        ).order_by(db.func.count(Asset.id).desc()).all()
        
        for location_name, count in locations_with_assets:
            print(f"  [LOC] {location_name}: {count} Assets")

if __name__ == "__main__":
    test_location_filter_fix()
