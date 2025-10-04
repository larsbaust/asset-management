#!/usr/bin/env python3
"""
Debug Dashboard Asset Counts - Prüft warum Dashboard nur +1 zeigt statt korrekte Anzahl
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import Asset, Location, Order, OrderItem
from datetime import datetime, timedelta

def debug_dashboard_counts():
    app = create_app()
    
    with app.app_context():
        print("=== DASHBOARD COUNT DEBUG ===")
        
        # 1. Alle Assets zählen
        total_assets = Asset.query.count()
        active_assets = Asset.query.filter_by(status='active').count()
        on_loan_assets = Asset.query.filter_by(status='on_loan').count()
        inactive_assets = Asset.query.filter(Asset.status.in_(['inactive', 'defect'])).count()
        
        print(f"Total Assets: {total_assets}")
        print(f"Active Assets: {active_assets}")
        print(f"On Loan Assets: {on_loan_assets}")
        print(f"Inactive Assets: {inactive_assets}")
        
        # 2. Assets nach Location gruppieren
        print("\n=== ASSETS NACH LOCATION ===")
        locations = Location.query.all()
        for location in locations:
            # Alte Methode: über location field
            old_count = Asset.query.filter_by(location=location.name, status='active').count()
            # Neue Methode: über location_id
            new_count = Asset.query.filter_by(location_id=location.id, status='active').count()
            print(f"{location.name}: Old={old_count}, New={new_count}")
        
        # 3. Frittenwerk Bielefeld spezifisch
        bielefeld = Location.query.filter_by(name='Frittenwerk Bielefeld').first()
        if bielefeld:
            print(f"\n=== FRITTENWERK BIELEFELD DETAILS ===")
            print(f"Location ID: {bielefeld.id}")
            
            # Alle Assets in Bielefeld
            bielefeld_assets = Asset.query.filter_by(location_id=bielefeld.id).all()
            print(f"Alle Assets in Bielefeld: {len(bielefeld_assets)}")
            
            # Aktive Assets in Bielefeld
            active_bielefeld = Asset.query.filter_by(location_id=bielefeld.id, status='active').all()
            print(f"Aktive Assets in Bielefeld: {len(active_bielefeld)}")
            
            # Assets nach Erstellungsdatum
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            
            assets_today = [a for a in active_bielefeld if a.created_at.date() == today]
            assets_yesterday = [a for a in active_bielefeld if a.created_at.date() == yesterday]
            
            print(f"Assets erstellt heute ({today}): {len(assets_today)}")
            print(f"Assets erstellt gestern ({yesterday}): {len(assets_yesterday)}")
            
            # Details der heute erstellten Assets
            if assets_today:
                print("\nHeute erstellte Assets:")
                for asset in assets_today:
                    print(f"  - {asset.name} (ID: {asset.id}) - Erstellt: {asset.created_at}")
        
        # 4. Prüfe recent orders mit Import
        print("\n=== RECENT ORDERS MIT IMPORT ===")
        recent_orders = Order.query.filter_by(status='erledigt').order_by(Order.id.desc()).limit(5).all()
        
        for order in recent_orders:
            print(f"\nOrder #{order.id} ({order.status}) - Location: {order.location}")
            order_items = OrderItem.query.filter_by(order_id=order.id).all()
            total_quantity = sum(item.quantity for item in order_items)
            print(f"  Bestellte Quantity: {total_quantity}")
            
            # Zugehörige Assets finden
            order_assets = Asset.query.filter_by(order_id=order.id).all()
            print(f"  Erstellte Assets: {len(order_assets)}")
            
            if order_assets:
                print("  Asset Details:")
                for asset in order_assets:
                    print(f"    - {asset.name} (Status: {asset.status}) - Erstellt: {asset.created_at}")

if __name__ == "__main__":
    debug_dashboard_counts()
