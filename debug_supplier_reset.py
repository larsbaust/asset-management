#!/usr/bin/env python3

from app import create_app
from app.models import db, Supplier
from sqlalchemy import text

def debug_supplier_reset():
    app = create_app()
    
    with app.app_context():
        print("=== SUPPLIER RESET DEBUG ===")
        
        # Check current suppliers
        suppliers = Supplier.query.all()
        print(f"\nAktuell {len(suppliers)} Lieferanten in der Datenbank:")
        for s in suppliers:
            print(f"  - ID {s.id}: {s.name}")
        
        # Check foreign key constraints
        print("\n=== FOREIGN KEY CONSTRAINTS ===")
        try:
            result = db.session.execute(text("""
                PRAGMA foreign_key_list(supplier);
            """))
            fks = result.fetchall()
            if fks:
                print("Foreign keys FROM supplier table:")
                for fk in fks:
                    print(f"  - {fk}")
            else:
                print("Keine Foreign Keys FROM supplier table")
        except Exception as e:
            print(f"Fehler beim Prüfen der Foreign Keys: {e}")
        
        # Check which tables reference supplier
        print("\n=== TABLES REFERENCING SUPPLIER ===")
        try:
            result = db.session.execute(text("""
                SELECT name, sql FROM sqlite_master 
                WHERE type='table' AND sql LIKE '%supplier%'
            """))
            tables = result.fetchall()
            for table in tables:
                print(f"Table: {table[0]}")
                print(f"SQL: {table[1]}")
                print()
        except Exception as e:
            print(f"Fehler beim Prüfen der Referenzen: {e}")
        
        # Try manual delete to see what happens
        print("\n=== MANUAL DELETE TEST ===")
        try:
            # Count before
            count_before = db.session.execute(text("SELECT COUNT(*) FROM supplier")).fetchone()[0]
            print(f"Lieferanten vor DELETE: {count_before}")
            
            # Try delete
            result = db.session.execute(text("DELETE FROM supplier"))
            print(f"DELETE statement rowcount: {result.rowcount}")
            
            # Count after (before commit)
            count_after = db.session.execute(text("SELECT COUNT(*) FROM supplier")).fetchone()[0]
            print(f"Lieferanten nach DELETE (vor Commit): {count_after}")
            
            # Rollback to not actually delete
            db.session.rollback()
            print("ROLLBACK ausgeführt - Daten nicht gelöscht")
            
        except Exception as e:
            print(f"Fehler beim manuellen DELETE: {e}")
            db.session.rollback()
        
        # Check if any assets reference suppliers
        print("\n=== ASSET SUPPLIER REFERENCES ===")
        try:
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM asset WHERE supplier_id IS NOT NULL
            """))
            asset_refs = result.fetchone()[0]
            print(f"Assets mit Supplier-Referenz: {asset_refs}")
            
            if asset_refs > 0:
                result = db.session.execute(text("""
                    SELECT a.id, a.name, a.supplier_id, s.name 
                    FROM asset a 
                    JOIN supplier s ON a.supplier_id = s.id 
                    LIMIT 5
                """))
                refs = result.fetchall()
                print("Beispiele:")
                for ref in refs:
                    print(f"  Asset {ref[0]} '{ref[1]}' -> Supplier {ref[2]} '{ref[3]}'")
                    
        except Exception as e:
            print(f"Fehler beim Prüfen der Asset-Referenzen: {e}")

if __name__ == "__main__":
    debug_supplier_reset()
