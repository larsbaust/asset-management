#!/usr/bin/env python3

from app import create_app
from app.models import db
from sqlalchemy import text

def debug_supplier_reset_detailed():
    app = create_app()
    
    with app.app_context():
        print("=== SUPPLIER RESET DETAILED DEBUG ===")
        
        # Check which tables exist
        print("\n=== EXISTING TABLES ===")
        result = db.session.execute(text("""
            SELECT name FROM sqlite_master WHERE type='table'
        """))
        tables = [row[0] for row in result.fetchall()]
        
        target_tables = ['asset_suppliers', 'order_template', 'order', 'supplier']
        for table in target_tables:
            if table in tables:
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = count_result.fetchone()[0]
                print(f"  {table}: EXISTS ({count} rows)")
            else:
                print(f"  {table}: DOES NOT EXIST")
        
        # Test deletion step by step
        print("\n=== STEP BY STEP DELETION TEST ===")
        
        tables_to_delete = ['asset_suppliers', 'order_template', 'order', 'supplier']
        
        for table in tables_to_delete:
            if table not in tables:
                print(f"SKIP {table}: Table does not exist")
                continue
                
            try:
                # Count before
                count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count_before = count_result.fetchone()[0]
                print(f"\nTesting {table}: {count_before} rows")
                
                if count_before > 0:
                    # Try delete
                    result = db.session.execute(text(f"DELETE FROM {table}"))
                    print(f"  DELETE successful: {result.rowcount} rows affected")
                    
                    # Count after
                    count_result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count_after = count_result.fetchone()[0]
                    print(f"  Rows after DELETE: {count_after}")
                else:
                    print(f"  Table {table} is empty, skipping")
                
                # Rollback to preserve data for next test
                db.session.rollback()
                print(f"  ROLLBACK executed")
                
            except Exception as e:
                print(f"  ERROR deleting from {table}: {e}")
                db.session.rollback()

if __name__ == "__main__":
    debug_supplier_reset_detailed()
