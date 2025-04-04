from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    # Benutzer finden
    user = User.query.filter_by(email='baust.lars@gmail.com').first()
    if user:
        # Neues Passwort setzen
        new_password = 'test123'
        user.password = generate_password_hash(new_password)
        db.session.commit()
        print(f"\nPasswort wurde zurückgesetzt für: {user.email}")
        print(f"Neues Passwort: {new_password}")
    else:
        print("Benutzer nicht gefunden")
