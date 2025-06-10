from app import create_app, db
from app.models import Permission

# Neue Chart-Berechtigungen
chart_permissions = [
    ('view_chart_asset_status', 'Chart: Asset-Status anzeigen'),
    ('view_chart_cost_distribution', 'Chart: Kostenverteilung anzeigen'),
    ('view_chart_value_development', 'Chart: Wertentwicklung anzeigen'),
    ('view_chart_categories', 'Chart: Kategorien-Statistik anzeigen'),
    ('view_chart_manufacturers', 'Chart: Hersteller-Statistik anzeigen'),
    ('view_chart_location_map', 'Chart: Standortkarte anzeigen'),
    ('view_chart_delivery_status', 'Chart: Lieferstatus anzeigen')
]

app = create_app()
with app.app_context():
    for name, desc in chart_permissions:
        # Prüfen, ob die Berechtigung bereits existiert
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
            print(f"Neue Chart-Berechtigung hinzugefügt: {name} ({desc})")
        else:
            print(f"Chart-Berechtigung existiert bereits: {name}")
            
    db.session.commit()
    print('Chart-Berechtigungen erfolgreich angelegt oder aktualisiert.')
