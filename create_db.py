from app import db, create_app

app = create_app()
with app.app_context():
    db.drop_all()  # Löscht alle existierenden Tabellen
    db.create_all()  # Erstellt die Tabellen neu
    print("Datenbank wurde neu erstellt!")
