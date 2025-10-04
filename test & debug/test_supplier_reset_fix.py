#!/usr/bin/env python3

from app import create_app
from app.admin import reset_suppliers_database
from app.models import db, Supplier

def test_supplier_reset_fix():
    app = create_app()
    
    with app.app_context():
        print("=== SUPPLIER RESET FIX TEST ===")
        
        # Check suppliers before
        suppliers_before = Supplier.query.all()
        print(f"\nLieferanten vor Reset: {len(suppliers_before)}")
        for s in suppliers_before:
            print(f"  - ID {s.id}: {s.name}")
        
        # Test the reset function
        print("\n=== RESET TEST ===")
        try:
            success, deleted = reset_suppliers_database()
            print(f"Reset erfolgreich: {success}")
            print(f"Gelöschte Daten: {deleted}")
            
            # Check suppliers after
            suppliers_after = Supplier.query.all()
            print(f"\nLieferanten nach Reset: {len(suppliers_after)}")
            
            if len(suppliers_after) == 0:
                print("✅ SUCCESS: Alle Lieferanten wurden gelöscht!")
            else:
                print("❌ FAILED: Lieferanten sind noch vorhanden:")
                for s in suppliers_after:
                    print(f"  - ID {s.id}: {s.name}")
                    
        except Exception as e:
            print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_supplier_reset_fix()
