from app import db, create_app
from app.models import Permission

permissions = [
    ('manage_users', 'Benutzerverwaltung'),
    ('manage_roles', 'Rollenverwaltung'),
    ('backup_data', 'Backup & Restore'),
    ('view_changelog', 'Changelog anzeigen'),
    ('view_asset_log', 'Asset-Logbuch anzeigen')
]

app = create_app()
with app.app_context():
    for name, desc in permissions:
        if not Permission.query.filter_by(name=name).first():
            db.session.add(Permission(name=name, description=desc))
    db.session.commit()
    print('Permissions erfolgreich angelegt oder aktualisiert.')
