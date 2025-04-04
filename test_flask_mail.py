from app import create_app, mail
from flask_mail import Message

app = create_app()

with app.app_context():
    try:
        print("\nVersuche Test-E-Mail zu senden...")
        msg = Message(
            'Test E-Mail',
            sender=app.config['MAIL_USERNAME'],
            recipients=[app.config['MAIL_USERNAME']]  # Sende an sich selbst
        )
        msg.body = "Dies ist eine Test-E-Mail vom Asset Management System."
        
        print("\nE-Mail-Details:")
        print(f"Von: {msg.sender}")
        print(f"An: {msg.recipients}")
        print(f"Betreff: {msg.subject}")
        print(f"Inhalt: {msg.body}")
        
        mail.send(msg)
        print("\nTest-E-Mail erfolgreich gesendet!")
        
    except Exception as e:
        import traceback
        print(f"\nFehler beim E-Mail-Versand:")
        print(f"Typ: {type(e).__name__}")
        print(f"Details: {str(e)}")
        print("\nMail-Konfiguration:")
        print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
        print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
        print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
        print(f"MAIL_USE_SSL: {app.config.get('MAIL_USE_SSL')}")
        print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
        print(f"MAIL_PASSWORD length: {len(app.config.get('MAIL_PASSWORD', ''))}")
        print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
        print("\nStacktrace:")
        print(traceback.format_exc())
