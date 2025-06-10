from app import create_app, db
from app.models import Permission

# Neue Import-Berechtigungen
new_permissions = [
    ('import_locations', 'Standorte per CSV importieren'),
    ('import_suppliers', 'Lieferanten per CSV importieren')
]

app = create_app()
with app.app_context():
    for name, desc in new_permissions:
        # Prüfen, ob die Berechtigung bereits existiert
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
            print(f"Neue Berechtigung hinzugefügt: {name} ({desc})")
        else:
            print(f"Berechtigung existiert bereits: {name}")
            
    db.session.commit()
    print('Import-Berechtigungen erfolgreich angelegt oder aktualisiert.')
