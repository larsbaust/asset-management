#!/usr/bin/env python3
"""
Verify Reset Coverage - Prüft welche Tabellen im Reset abgedeckt sind
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def verify_reset_coverage():
    app = create_app()
    
    with app.app_context():
        print("=== RESET COVERAGE VERIFICATION ===")
        
        # 1. Alle Tabellen in der Datenbank auflisten
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
        all_tables = [row[0] for row in result.fetchall()]
        
        print(f"\n=== ALLE TABELLEN IN DB ({len(all_tables)}) ===")
        for table in sorted(all_tables):
            print(f"  - {table}")
        
        # 2. Tabellen die im Reset abgedeckt sind
        covered_tables = {
            # Assets Reset
            'asset_log': 'Assets',
            'inventory_item': 'Assets', 
            'loan': 'Assets',
            'document': 'Assets (teilweise - nur mit asset_id)',
            'cost_entry': 'Assets',
            'asset_suppliers': 'Assets',
            'asset_manufacturers': 'Assets',
            'asset': 'Assets',
            
            # Orders Reset
            'order_item': 'Orders',
            'order': 'Orders',
            
            # Inventory Reset  
            'inventory_team': 'Inventory',
            'inventory_session': 'Inventory',
            
            # Optional Resets
            'supplier': 'Optional',
            'location': 'Optional', 
            'manufacturer': 'Optional',
            'assignment': 'Optional'
        }
        
        print(f"\n=== ABGEDECKTE TABELLEN ({len(covered_tables)}) ===")
        for table, category in covered_tables.items():
            status = "[OK]" if table in all_tables else "[MISSING]"
            print(f"  {status} {table} ({category})")
        
        # 3. Nicht abgedeckte Tabellen identifizieren
        not_covered = set(all_tables) - set(covered_tables.keys())
        
        print(f"\n=== NICHT ABGEDECKTE TABELLEN ({len(not_covered)}) ===")
        for table in sorted(not_covered):
            # Zähle Einträge in der Tabelle
            try:
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.fetchone()[0]
                print(f"  [MISSING] {table} ({count} Einträge)")
            except Exception as e:
                print(f"  [ERROR] {table} (Fehler beim Zählen: {e})")
        
        # 4. Kritische fehlende Tabellen bewerten
        critical_missing = []
        for table in not_covered:
            if any(keyword in table.lower() for keyword in ['asset', 'order', 'loan', 'inventory']):
                critical_missing.append(table)
        
        if critical_missing:
            print(f"\n=== KRITISCH FEHLENDE TABELLEN ===")
            for table in critical_missing:
                print(f"  [CRITICAL] {table}")
        
        # 5. Template Bug Check
        print(f"\n=== TEMPLATE BUG CHECK ===")
        template_path = r"c:\Users\baust\CascadeProjects\Assed Managemend\app\templates\md3\admin\reset_data.html"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()
                
            # Bug: admin.py sucht nach 'confirmation_text', aber Template hat 'confirmation-input'
            if 'id="confirmation-input"' in template_content:
                print("  [BUG] Template verwendet 'confirmation-input' aber admin.py sucht 'confirmation_text'")
            else:
                print("  [OK] Template confirmation ID korrekt")
                
        except Exception as e:
            print(f"  [ERROR] Fehler beim Template-Check: {e}")

if __name__ == "__main__":
    verify_reset_coverage()
