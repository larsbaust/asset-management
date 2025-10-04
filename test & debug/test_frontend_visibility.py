#!/usr/bin/env python3
"""
Test Frontend Asset Visibility - Simuliert MD3 Assets Route und prüft JavaScript Filtering
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Asset, Location
from flask import url_for
import requests
from datetime import datetime

def test_frontend_visibility():
    app = create_app()
    
    with app.app_context():
        print("=== FRONTEND VISIBILITY TEST ===")
        
        # 1. MD3 Assets Route direkt testen
        with app.test_client() as client:
            print("\n=== MD3 ASSETS ROUTE TEST ===")
            
            # Test ohne Filter
            response = client.get('/md3/assets')
            print(f"[HTTP] Status ohne Filter: {response.status_code}")
            
            if response.status_code == 200:
                html_content = response.get_data(as_text=True)
                
                # Prüfe ob Bielefeld Assets im HTML sind
                bielefeld_assets = Asset.query.join(Asset.location_obj).filter(
                    Location.name == 'Frittenwerk Bielefeld',
                    Asset.status == 'active'
                ).all()
                
                print(f"[DB] Bielefeld Assets in DB: {len(bielefeld_assets)}")
                
                assets_in_html = 0
                for asset in bielefeld_assets:
                    if asset.name in html_content:
                        assets_in_html += 1
                        print(f"  [FOUND] {asset.name} in HTML")
                    else:
                        print(f"  [MISSING] {asset.name} NOT in HTML")
                
                print(f"[HTML] Assets gefunden im HTML: {assets_in_html}/{len(bielefeld_assets)}")
                
                # Prüfe JavaScript Table Filtering
                if 'filterTable' in html_content:
                    print("[JS] JavaScript filterTable funktion gefunden")
                else:
                    print("[JS] JavaScript filterTable funktion FEHLT")
                
                # Prüfe Location Filter
                if 'location' in html_content and 'filter' in html_content:
                    print("[FILTER] Location Filter im HTML gefunden")
                else:
                    print("[FILTER] Location Filter im HTML FEHLT")
            
            # Test mit Location Filter
            print(f"\n=== MD3 ASSETS MIT LOCATION FILTER ===")
            response_filtered = client.get('/md3/assets?location=Frittenwerk Bielefeld')
            print(f"[HTTP] Status mit Location Filter: {response_filtered.status_code}")
            
            if response_filtered.status_code == 200:
                filtered_html = response_filtered.get_data(as_text=True)
                
                # Zähle Tabellen-Zeilen in gefilterter Ansicht
                table_rows = filtered_html.count('<tr class="asset-row')
                print(f"[FILTERED] Tabellen-Zeilen in gefilterter Ansicht: {table_rows}")
                
                # Prüfe ob Bielefeld Assets sichtbar sind
                bielefeld_visible = 0
                for asset in bielefeld_assets:
                    if asset.name in filtered_html:
                        bielefeld_visible += 1
                
                print(f"[FILTERED] Bielefeld Assets sichtbar: {bielefeld_visible}/{len(bielefeld_assets)}")
            
            # Test Status Filter
            print(f"\n=== STATUS FILTER TEST ===")
            response_status = client.get('/md3/assets?status=active')
            print(f"[HTTP] Status Filter (active): {response_status.status_code}")
            
            if response_status.status_code == 200:
                status_html = response_status.get_data(as_text=True)
                active_rows = status_html.count('<tr class="asset-row')
                print(f"[STATUS] Aktive Asset-Zeilen: {active_rows}")
                
                # Vergleiche mit DB Count
                active_count_db = Asset.query.filter_by(status='active').count()
                print(f"[STATUS] Aktive Assets in DB: {active_count_db}")
                
                if active_rows > 0:
                    print("[STATUS] Status Filter funktioniert")
                else:
                    print("[STATUS] Status Filter hat Problem")

        # 2. Template Asset Assignment prüfen
        print(f"\n=== TEMPLATE ASSET ASSIGNMENT ===")
        
        # Hole die Route-Handler Logik
        from app.routes import md3_assets
        
        # Simuliere Request Context für Route
        with app.test_request_context('/md3/assets?location=Frittenwerk Bielefeld'):
            try:
                # Route-Handler direkt aufrufen (ohne HTTP)
                from flask import request
                print(f"[ROUTE] Location Parameter: {request.args.get('location', 'None')}")
                print(f"[ROUTE] Status Parameter: {request.args.get('status', 'active')}")
                
                # Assets Query wie in Route
                from app.models import Category, Manufacturer, Supplier, Assignment
                
                query = Asset.query
                location = request.args.get('location', '')
                status = request.args.get('status', 'active')
                
                if location:
                    query = query.join(Asset.location_obj).filter(Location.name.ilike(f'%{location}%'))
                
                if status != 'all':
                    query = query.filter(Asset.status == status)
                
                assets = query.all()
                print(f"[ROUTE] Query Ergebnis: {len(assets)} Assets")
                
                for asset in assets[:3]:  # Nur erste 3 zeigen
                    print(f"  [ASSET] {asset.name} - Status: {asset.status} - Location: {asset.location_obj.name if asset.location_obj else 'None'}")
                    
            except Exception as e:
                print(f"[ERROR] Route Simulation Fehler: {e}")

if __name__ == "__main__":
    test_frontend_visibility()
