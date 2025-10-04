#!/usr/bin/env python3
"""
Debug Script: Chart-Daten Generation nach Reset prüfen
Simuliert genau was das Dashboard-Backend für Chart-Daten generiert
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.models import db, Asset, Order, OrderItem, Supplier, Location, Category, Manufacturer
from sqlalchemy import func
from datetime import datetime
from dateutil.relativedelta import relativedelta

def debug_chart_data_generation():
    """Simuliert genau die Dashboard Chart-Daten Generation"""
    
    print("=== CHART DATEN GENERATION DEBUG ===\n")
    
    # 1. Asset Counts (wie im Dashboard)
    total_assets = Asset.query.count()
    active = Asset.query.filter_by(status='active').count()
    on_loan = Asset.query.filter_by(status='on_loan').count()
    inactive = Asset.query.filter(Asset.status.in_(['inactive', 'defect'])).count()
    
    print(f"=== ASSET STATUS COUNTS ===")
    print(f"Total Assets: {total_assets}")
    print(f"Active: {active}")
    print(f"On Loan: {on_loan}")
    print(f"Inactive: {inactive}")
    
    # 2. Wertentwicklung (wie im Dashboard)
    print(f"\n=== WERTENTWICKLUNG ===")
    months = []
    values = []
    
    if total_assets > 0:
        today = datetime.utcnow()
        for i in range(5, -1, -1):
            date = today.replace(day=1) - relativedelta(months=i)
            next_date = date + relativedelta(months=1)
            months.append(date.strftime('%B %Y'))
            
            all_assets = Asset.query.all()
            total_value = 0
            for asset in all_assets:
                asset_date = getattr(asset, 'purchase_date', None) or asset.created_at
                if asset_date and asset_date < next_date:
                    try:
                        if asset.value is not None:
                            total_value += float(asset.value)
                    except (ValueError, TypeError):
                        continue
            values.append(total_value)
    
    print(f"Months: {months}")
    print(f"Values: {values}")
    
    # 3. Kostentypes (wie im Dashboard)
    print(f"\n=== KOSTENVERTEILUNG ===")
    costs = {'Anschaffung': 0}
    all_assets = Asset.query.all()
    
    for asset in all_assets:
        if asset.value:
            costs['Anschaffung'] += float(asset.value)
    
    costs = {k: v for k, v in costs.items() if v > 0}
    cost_type_labels = list(costs.keys())
    cost_amounts = list(costs.values())
    
    print(f"Cost Labels: {cost_type_labels}")
    print(f"Cost Amounts: {cost_amounts}")
    
    # 4. Kategorien (wie im Dashboard)
    print(f"\n=== KATEGORIEN VERTEILUNG ===")
    categories = db.session.query(
        Category.name,
        func.count(Asset.id)
    ).outerjoin(Asset, (Asset.category_id == Category.id) & (Asset.status == 'active'))\
     .group_by(Category.id, Category.name)\
     .order_by(Category.name)\
     .all()
     
    category_data = [{
        'category': cat_name or 'Ohne Kategorie',
        'count': count
    } for cat_name, count in categories]
    
    # Assets ohne Kategorie ergänzen (nur aktive)
    no_category_count = Asset.query.filter((Asset.category == None) & (Asset.status == 'active')).count()
    if no_category_count:
        category_data.append({'category': 'Ohne Kategorie', 'count': no_category_count})
    
    print(f"Category Data: {category_data}")
    
    # 5. MD3 Chart Data (wie im Dashboard)
    print(f"\n=== MD3 CHART DATA ===")
    md3_chart_data = {
        'cost_distribution': {
            'labels': cost_type_labels,
            'data': cost_amounts
        },
        'value_development': {
            'labels': months,
            'data': values
        },
        'department_distribution': {
            'labels': [cat['category'] for cat in category_data if cat['count'] > 0],
            'data': [cat['count'] for cat in category_data if cat['count'] > 0]
        },
        'monthly_usage': {
            'labels': [],
            'data': []
        }
    }
    
    print("MD3 Chart Data:")
    for key, value in md3_chart_data.items():
        print(f"  {key}: {value}")
    
    # 6. Überprüfung ob Charts leer sein sollten
    print(f"\n=== CHART LEER-CHECK ===")
    charts_should_be_empty = total_assets == 0
    print(f"Charts sollten leer sein: {charts_should_be_empty}")
    
    if not charts_should_be_empty:
        print("❌ PROBLEM: Assets sind noch vorhanden!")
        print("Assets in DB:")
        for asset in Asset.query.all():
            print(f"  - {asset.name} (Status: {asset.status}, Wert: {asset.value})")
    
    # 7. Cache-verdächtige Daten
    print(f"\n=== MÖGLICHE CACHE-QUELLEN ===")
    print(f"Supplier count: {Supplier.query.count()}")
    print(f"Location count: {Location.query.count()}")
    print(f"Category count: {Category.query.count()}")
    print(f"Manufacturer count: {Manufacturer.query.count()}")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        debug_chart_data_generation()
