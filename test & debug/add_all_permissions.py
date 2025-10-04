"""
Skript zum Anlegen ALLER Permissions für das Asset Management System
Führt alle Permission-Skripte zusammen aus
"""
from app import create_app, db
from app.models import Permission

# ALLE Permissions (21 Stück)
all_permissions = [
    # Assets (6)
    ('archive_asset', 'Assets archivieren'),
    ('delete_assets', 'Assets löschen'),
    ('edit_assets', 'Assets bearbeiten'),
    ('restore_asset', 'Archivierte Assets wiederherstellen'),
    ('view_assets', 'Assets anzeigen'),
    
    # Administration (2)
    ('manage_roles', 'Rollenverwaltung'),
    ('manage_users', 'Benutzerverwaltung'),
    
    # Import (3)
    ('import_csv', 'CSV-Import'),
    ('import_locations', 'Standorte per CSV importieren'),
    ('import_suppliers', 'Lieferanten per CSV importieren'),
    
    # Backup (2)
    ('backup_data', 'Backup erstellen'),
    ('restore_data', 'Backup wiederherstellen'),
    
    # Charts (7)
    ('view_chart_asset_status', 'Chart: Asset-Status anzeigen'),
    ('view_chart_categories', 'Chart: Kategorien-Statistik anzeigen'),
    ('view_chart_cost_distribution', 'Chart: Kostenverteilung anzeigen'),
    ('view_chart_delivery_status', 'Chart: Lieferstatus anzeigen'),
    ('view_chart_location_map', 'Chart: Standortkarte anzeigen'),
    ('view_chart_manufacturers', 'Chart: Hersteller-Statistik anzeigen'),
    ('view_chart_value_development', 'Chart: Wertentwicklung anzeigen'),
    
    # Logs (2)
    ('view_asset_log', 'Asset-Logbuch anzeigen'),
    ('view_changelog', 'Changelog anzeigen'),
]

app = create_app()
with app.app_context():
    print("=" * 70)
    print("ALLE PERMISSIONS ANLEGEN")
    print("=" * 70)
    
    added_count = 0
    existing_count = 0
    
    for name, desc in sorted(all_permissions):
        existing = Permission.query.filter_by(name=name).first()
        if not existing:
            db.session.add(Permission(name=name, description=desc))
            print(f"[+] NEU: {name:40s} - {desc}")
            added_count += 1
        else:
            print(f"[=] EXISTS: {name:40s} - {desc}")
            existing_count += 1
    
    db.session.commit()
    
    print("=" * 70)
    print(f"FERTIG! {added_count} neue Permissions hinzugefügt.")
    print(f"        {existing_count} Permissions existierten bereits.")
    print(f"        {added_count + existing_count} Permissions insgesamt.")
    print("=" * 70)
    
    # Überprüfung
    all_perms = Permission.query.order_by(Permission.name).all()
    print(f"\nAlle Permissions in der Datenbank ({len(all_perms)}):")
    for p in all_perms:
        print(f"   - {p.name:40s} | {p.description}")
