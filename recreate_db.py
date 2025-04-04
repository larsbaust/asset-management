from app import create_app, db
from app.models import User

app = create_app()

with app.app_context():
    print("Lösche alle Tabellen...")
    db.drop_all()
    print("Erstelle Tabellen neu...")
    db.create_all()
    print("Datenbank wurde erfolgreich neu erstellt!")
