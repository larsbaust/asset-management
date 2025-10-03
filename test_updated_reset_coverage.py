#!/usr/bin/env python3
"""
Test Updated Reset Coverage - Verifiziert die aktualisierte Reset-Funktion
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def test_updated_reset_coverage():
    app = create_app()
    
    with app.app_context():
        print("=== UPDATED RESET COVERAGE TEST ===")
        
        # Alle Tabellen in der DB
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        all_tables = [row[0] for row in result.fetchall()]
        
        # Aktualisierte abgedeckte Tabellen
        covered_tables = {
            # Assets Reset (erweitert)
            'asset_log': 'Assets',
            'inventory_item': 'Assets', 
            'loan': 'Assets',
            'multi_loan_asset': 'Assets (NEU)',
            'multi_loan': 'Assets (NEU)',
            'document': 'Assets (teilweise)',
            'cost_entry': 'Assets',
            'asset_assignments': 'Assets (NEU)',
            'asset_suppliers': 'Assets',
            'asset_manufacturers': 'Assets',
            'asset': 'Assets',
            
            # Orders Reset (erweitert)
            'order_template_item': 'Orders (NEU)',
            'order_template': 'Orders (NEU)', 
            'order_comment': 'Orders (NEU)',
            'order_item': 'Orders',
            '"order"': 'Orders',
            
            # Inventory Reset (erweitert)
            'inventory_team': 'Inventory',
            'inventory_session': 'Inventory',
            'inventory_planning': 'Inventory (NEU)',
            
            # Optional Resets
            'supplier': 'Optional',
            'location': 'Optional', 
            'manufacturer': 'Optional',
            'assignment': 'Optional'
        }
        
        print(f"\n=== AKTUALISIERTE ABDECKUNG ({len(covered_tables)}/32) ===")
        
        # Kategorien zählen
        categories = {}
        for table, category in covered_tables.items():
            if table in all_tables:
                if category not in categories:
                    categories[category] = []
                categories[category].append(table)
        
        for category, tables in sorted(categories.items()):
            print(f"\n{category} ({len(tables)} Tabellen):")
            for table in tables:
                # Handle SQL reserved keywords
                table_query = f'"{table}"' if table == 'order' else table
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_query}"))
                count = count_result.fetchone()[0]
                print(f"  [OK] {table} ({count} Einträge)")
        
        # Verbleibende nicht abgedeckte Tabellen
        not_covered = set(all_tables) - set(covered_tables.keys())
        
        print(f"\n=== VERBLEIBENDE NICHT ABGEDECKTE ({len(not_covered)}) ===")
        for table in sorted(not_covered):
            try:
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.fetchone()[0]
                
                # Bewertung der Wichtigkeit
                if table in ['user', 'role', 'permission', 'role_permissions']:
                    status = "[KEEP] System/Auth"
                elif table in ['alembic_version']:
                    status = "[KEEP] Migration"
                elif table in ['category']:
                    status = "[KEEP] Stammdaten"
                elif table in ['message']:
                    status = "[OPTIONAL] Nachrichten"
                elif count == 0:
                    status = "[EMPTY] Leer"
                else:
                    status = "[REVIEW] Prüfen"
                    
                print(f"  {status} {table} ({count} Einträge)")
            except Exception as e:
                print(f"  [ERROR] {table} (Fehler: {e})")
        
        # Abdeckungsstatistik
        coverage_percent = (len(covered_tables) / len(all_tables)) * 100
        print(f"\n=== COVERAGE STATISTIK ===")
        print(f"Abgedeckte Tabellen: {len(covered_tables)}/{len(all_tables)} ({coverage_percent:.1f}%)")
        
        # Kritische Assets/Orders/Inventory Tabellen
        critical_keywords = ['asset', 'order', 'loan', 'inventory']
        critical_tables = [t for t in all_tables if any(kw in t.lower() for kw in critical_keywords)]
        covered_critical = [t for t in critical_tables if t in covered_tables]
        
        print(f"Kritische Tabellen abgedeckt: {len(covered_critical)}/{len(critical_tables)}")
        
        # Reset Safety Assessment
        print(f"\n=== RESET SAFETY ASSESSMENT ===")
        if len(not_covered & set(['user', 'role', 'permission'])) == 3:
            print("[SAFE] Benutzer/Rollen bleiben erhalten")
        else:
            print("[WARNING] Benutzer/Rollen könnten betroffen sein")
            
        if 'category' not in covered_tables:
            print("[SAFE] Kategorien bleiben erhalten")
        else:
            print("[WARNING] Kategorien werden gelöscht")

if __name__ == "__main__":
    test_updated_reset_coverage()
