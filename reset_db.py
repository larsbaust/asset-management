from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print("\nLösche alle Benutzer aus der Datenbank...")
    User.query.delete()
    db.session.commit()
    print("Datenbank wurde erfolgreich zurückgesetzt!")
    
    # Überprüfe, ob alle Benutzer gelöscht wurden
    users = User.query.all()
    if not users:
        print("Bestätigung: Keine Benutzer in der Datenbank.\n")
    else:
        print(f"Warnung: Es sind noch {len(users)} Benutzer in der Datenbank!\n")
