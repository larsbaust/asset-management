#!/usr/bin/env python3
"""
Umfassendes Permission-Initialisierungs-Skript
Erstellt ALLE Berechtigungen für das Asset Management System
"""

from app import create_app, db
from app.models import Permission

# Vollständige Liste aller Berechtigungen (basierend auf aktueller App-Struktur)
ALL_PERMISSIONS = [
    # === Assets ===
    ('view_assets', 'Assets anzeigen'),
    ('edit_assets', 'Assets bearbeiten'),
    ('delete_assets', 'Assets löschen'),
    ('archive_asset', 'Assets archivieren'),
    ('restore_asset', 'Archivierte Assets wiederherstellen'),
    ('import_csv', 'CSV-Import für Assets'),
    ('view_asset_log', 'Asset-Logbuch anzeigen'),
    
    # === Dashboard ===
    ('view_dashboard', 'Dashboard anzeigen'),
    
    # === Administration ===
    ('manage_users', 'Benutzerverwaltung'),
    ('manage_roles', 'Rollenverwaltung'),
    ('view_changelog', 'Changelog anzeigen'),
    
    # === Bestellung ===
    ('manage_orders', 'Bestellungen verwalten'),
    ('view_orders', 'Bestellungen anzeigen'),
    ('edit_orders', 'Bestellungen bearbeiten'),
    ('delete_orders', 'Bestellungen löschen'),
    
    # === Inventur ===
    ('manage_inventory', 'Inventur verwalten'),
    ('view_inventory', 'Inventur anzeigen'),
    ('edit_inventory', 'Inventur bearbeiten'),
    
    # === Charts ===
    ('view_chart_asset_status', 'Chart: Asset-Status anzeigen'),
    ('view_chart_cost_distribution', 'Chart: Kostenverteilung anzeigen'),
    ('view_chart_value_development', 'Chart: Wertentwicklung anzeigen'),
    ('view_chart_categories', 'Chart: Kategorien-Statistik anzeigen'),
    ('view_chart_manufacturers', 'Chart: Hersteller-Statistik anzeigen'),
    ('view_chart_location_map', 'Chart: Standortkarte anzeigen'),
    ('view_chart_locations_map', 'Chart: Standortkarte (alternative) anzeigen'),
    ('view_chart_delivery_status', 'Chart: Lieferstatus anzeigen'),
    
    # === Reports ===
    ('export_csv', 'CSV-Export für Berichte'),
    ('reports_csv', 'Reports als CSV exportieren'),
    
    # === Backup ===
    ('backup_data', 'Backup erstellen'),
    ('restore_data', 'Backup wiederherstellen'),
    ('archive_data', 'Daten archivieren'),
    
    # === Standorte ===
    ('manage_locations', 'Standorte verwalten'),
    ('view_locations', 'Standorte anzeigen'),
    ('edit_locations', 'Standorte bearbeiten'),
    ('delete_locations', 'Standorte löschen'),
    ('import_locations', 'Standorte per CSV importieren'),
    
    # === Lieferanten ===
    ('manage_suppliers', 'Lieferanten verwalten'),
    ('view_suppliers', 'Lieferanten anzeigen'),
    ('edit_suppliers', 'Lieferanten bearbeiten'),
    ('delete_suppliers', 'Lieferanten löschen'),
    ('import_suppliers', 'Lieferanten per CSV importieren'),
    
    # === Hersteller ===
    ('manage_manufacturers', 'Hersteller verwalten'),
    ('view_manufacturers', 'Hersteller anzeigen'),
    ('edit_manufacturers', 'Hersteller bearbeiten'),
    ('delete_manufacturers', 'Hersteller löschen'),
    
    # === Kategorien ===
    ('manage_categories', 'Kategorien verwalten'),
    ('view_categories', 'Kategorien anzeigen'),
    ('edit_categories', 'Kategorien bearbeiten'),
    ('delete_categories', 'Kategorien löschen'),
    
    # === Ausleihen ===
    ('manage_loans', 'Ausleihen verwalten'),
    ('view_loans', 'Ausleihen anzeigen'),
    ('edit_loans', 'Ausleihen bearbeiten'),
    ('delete_loans', 'Ausleihen löschen'),
    
    # === Wartung ===
    ('manage_maintenance', 'Wartungen verwalten'),
    ('view_maintenance', 'Wartungen anzeigen'),
    ('edit_maintenance', 'Wartungen bearbeiten'),
    ('delete_maintenance', 'Wartungen löschen'),
]

def init_all_permissions():
    """Initialisiert alle Permissions in der Datenbank"""
    app = create_app()
    
    with app.app_context():
        added_count = 0
        existing_count = 0
        
        print("=" * 60)
        print("Initialisiere Berechtigungen...")
        print("=" * 60)
        
        for name, description in ALL_PERMISSIONS:
            existing = Permission.query.filter_by(name=name).first()
            
            if not existing:
                perm = Permission(name=name, description=description)
                db.session.add(perm)
                added_count += 1
                print(f"✅ NEU: {name} - {description}")
            else:
                existing_count += 1
                print(f"⏭️  Existiert bereits: {name}")
        
        try:
            db.session.commit()
            print("\n" + "=" * 60)
            print(f"✅ Erfolgreich! {added_count} neue Berechtigungen hinzugefügt.")
            print(f"ℹ️  {existing_count} Berechtigungen existierten bereits.")
            print(f"📊 Gesamt: {added_count + existing_count} Berechtigungen")
            print("=" * 60)
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Fehler beim Speichern: {e}")
            raise

if __name__ == '__main__':
    init_all_permissions()
