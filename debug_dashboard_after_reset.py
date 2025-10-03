#!/usr/bin/env python3
"""
Debug Script: Dashboard Daten nach Reset prüfen
Überprüft, welche Daten noch im Dashboard angezeigt werden nach einem Reset.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Asset, Order, OrderItem, Supplier, Location, Category, Manufacturer
from app.models import InventorySession, InventoryItem, CostEntry, Loan, AssetLog
from sqlalchemy import text, func

def debug_dashboard_after_reset():
    """Prüft Dashboard-relevante Daten nach Reset"""
    
    print("=== DASHBOARD DATEN NACH RESET ===\n")
    
    # 1. Asset-bezogene Daten prüfen
    print("=== ASSETS & VERWANDTE DATEN ===")
    assets_count = Asset.query.count()
    print(f"Assets: {assets_count}")
    
    # Asset-Status Verteilung (für Donut Chart)
    if assets_count > 0:
        status_counts = db.session.query(
            Asset.status,
            func.count(Asset.id)
        ).group_by(Asset.status).all()
        print("Asset Status Verteilung:")
        for status, count in status_counts:
            print(f"  - {status}: {count}")
    
    # Asset-Logs
    asset_logs = AssetLog.query.count()
    print(f"Asset Logs: {asset_logs}")
    
    # Kosten
    cost_entries = CostEntry.query.count()
    print(f"Kosteneinträge: {cost_entries}")
    
    # Loans
    loans = Loan.query.count()
    print(f"Ausleihungen: {loans}")
    
    print()
    
    # 2. Bestellungen
    print("=== BESTELLUNGEN ===")
    orders_count = Order.query.count()
    print(f"Bestellungen: {orders_count}")
    
    order_items_count = OrderItem.query.count()
    print(f"Bestellpositionen: {order_items_count}")
    
    # Bestellstatus (für Charts)
    if orders_count > 0:
        order_status_counts = db.session.query(
            Order.status,
            func.count(Order.id)
        ).group_by(Order.status).all()
        print("Bestellstatus Verteilung:")
        for status, count in order_status_counts:
            print(f"  - {status}: {count}")
    
    print()
    
    # 3. Inventur
    print("=== INVENTUR ===")
    inventory_sessions = InventorySession.query.count()
    print(f"Inventur Sessions: {inventory_sessions}")
    
    inventory_items = InventoryItem.query.count()
    print(f"Inventur Items: {inventory_items}")
    
    print()
    
    # 4. Stammdaten (sollten erhalten bleiben)
    print("=== STAMMDATEN (SOLLEN ERHALTEN BLEIBEN) ===")
    suppliers_count = Supplier.query.count()
    locations_count = Location.query.count()
    categories_count = Category.query.count()
    manufacturers_count = Manufacturer.query.count()
    
    print(f"Lieferanten: {suppliers_count}")
    print(f"Standorte: {locations_count}")
    print(f"Kategorien: {categories_count}")
    print(f"Hersteller: {manufacturers_count}")
    
    print()
    
    # 5. Spezielle Dashboard-Abfragen simulieren
    print("=== DASHBOARD CHART DATEN SIMULATION ===")
    
    # Asset nach Standort (für Location Charts)
    location_asset_counts = db.session.query(
        Location.name,
        func.count(Asset.id).label('asset_count')
    ).outerjoin(Asset, Asset.location_id == Location.id)\
     .group_by(Location.id, Location.name).all()
    
    print("Assets pro Standort:")
    for location_name, asset_count in location_asset_counts:
        print(f"  - {location_name}: {asset_count}")
    
    # Wert-Entwicklung (basierend auf CostEntry)
    if cost_entries > 0:
        total_value = db.session.query(func.sum(CostEntry.amount)).scalar() or 0
        print(f"Gesamtwert (Kosteneintäge): {total_value}")
    else:
        print("Gesamtwert: 0 (keine Kosteneinträge)")
    
    print()
    
    # 6. Zusammenfassung
    print("=== ZUSAMMENFASSUNG ===")
    should_be_empty = [
        ("Assets", assets_count),
        ("Bestellungen", orders_count),
        ("Inventur Sessions", inventory_sessions),
        ("Asset Logs", asset_logs),
        ("Kosteneinträge", cost_entries),
        ("Ausleihungen", loans)
    ]
    
    print("Diese Werte sollten nach Reset 0 sein:")
    all_empty = True
    for name, count in should_be_empty:
        status = "✅ LEER" if count == 0 else "❌ HAT DATEN"
        print(f"  {name}: {count} {status}")
        if count > 0:
            all_empty = False
    
    print("\n" + "="*50)
    if all_empty:
        print("✅ DASHBOARD SOLLTE LEER SEIN - Reset war erfolgreich!")
    else:
        print("❌ DASHBOARD ZEIGT NOCH DATEN - Mögliche Verknüpfungsfehler!")
        
    print("="*50)

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        debug_dashboard_after_reset()
