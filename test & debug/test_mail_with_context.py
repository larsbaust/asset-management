from app import create_app, mail
from flask_mail import Message
from flask import current_app

app = create_app()

def test_mail():
    print("\n=== Test-E-Mail mit App-Kontext ===")
    
    with app.app_context():
        print("\nApp-Kontext Status:")
        print(f"App-Kontext aktiv: {current_app is not None}")
        
        try:
            print("\nErstelle Test-E-Mail...")
            msg = Message(
                'Test E-Mail mit Kontext',
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=['lars.baust@frittenwerk.com']
            )
            msg.body = "Dies ist eine Test-E-Mail vom Asset Management System (mit App-Kontext)."
            
            print("\nMail-Konfiguration:")
            print(f"MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
            print(f"MAIL_PORT: {app.config.get('MAIL_PORT')}")
            print(f"MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
            print(f"MAIL_USE_SSL: {app.config.get('MAIL_USE_SSL')}")
            print(f"MAIL_USERNAME: {app.config.get('MAIL_USERNAME')}")
            print(f"MAIL_PASSWORD length: {len(app.config.get('MAIL_PASSWORD', ''))}")
            print(f"MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
            
            print("\nE-Mail-Details:")
            print(f"Von: {msg.sender}")
            print(f"An: {msg.recipients}")
            print(f"Betreff: {msg.subject}")
            
            print("\nVersuche E-Mail zu senden...")
            mail.send(msg)
            print("E-Mail erfolgreich gesendet!")
            
        except Exception as e:
            import traceback
            print(f"\nFehler beim E-Mail-Versand:")
            print(f"Typ: {type(e).__name__}")
            print(f"Details: {str(e)}")
            print("\nStacktrace:")
            print(traceback.format_exc())
    
    print("\n=== Test Ende ===")

if __name__ == '__main__':
    test_mail()
