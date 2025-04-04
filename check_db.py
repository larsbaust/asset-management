from app.models import User
from app import create_app

app = create_app()

with app.app_context():
    print("\nBenutzer in der Datenbank:")
    users = User.query.all()
    for user in users:
        print(f"ID: {user.id}, Email: {user.email}, Bestätigt: {user.email_confirmed}")
