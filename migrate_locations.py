from app import create_app, db
from app.models import Asset, Location

app = create_app()

with app.app_context():
    # Schritt 1: Alle unterschiedlichen Standortnamen aus Assets holen
    location_names = set(
        asset.location.strip() for asset in Asset.query.all()
        if asset.location and asset.location.strip() != ''
    )
    print(f"Gefundene Standorte: {location_names}")

    # Schritt 2: Für jeden Standortnamen einen Location-Datensatz anlegen (falls nicht vorhanden)
    name_to_location = {}
    for name in location_names:
        location = Location.query.filter_by(name=name).first()
        if not location:
            location = Location(name=name)
            db.session.add(location)
            print(f"Location angelegt: {name}")
        else:
            print(f"Location existiert schon: {name}")
        name_to_location[name] = location
    db.session.commit()

    # Schritt 3: Assets auf Location-ID mappen
    updated = 0
    for asset in Asset.query.all():
        if asset.location and asset.location.strip() != '':
            loc = name_to_location.get(asset.location.strip())
            if loc:
                asset.location_id = loc.id
                updated += 1
    db.session.commit()
    print(f"{updated} Assets wurden mit location_id verknüpft.")

print("Migration abgeschlossen. Prüfe die Datenbank und entferne das alte Feld 'location' bei Bedarf.")
