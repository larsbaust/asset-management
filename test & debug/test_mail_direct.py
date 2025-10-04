import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_smtp_connection():
    print("\n=== SMTP Verbindungstest ===")
    
    # E-Mail-Konfiguration
    smtp_server = "smtp.gmail.com"
    smtp_port = 465
    username = os.getenv('MAIL_USERNAME', '').strip()
    password = os.getenv('MAIL_PASSWORD', '').strip()
    
    print(f"\nKonfiguration:")
    print(f"Server: {smtp_server}")
    print(f"Port: {smtp_port}")
    print(f"Benutzername: {username}")
    print(f"Passwort-Länge: {len(password)}")
    
    try:
        print("\nVerbinde mit SMTP-Server...")
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            print("Verbindung hergestellt!")
            
            print("\nVersuche Login...")
            server.login(username, password)
            print("Login erfolgreich!")
            
            # Erstelle Test-E-Mail
            print("\nErstelle Test-E-Mail...")
            msg = MIMEMultipart()
            msg['From'] = username
            msg['To'] = 'lars.baust@frittenwerk.com'
            msg['Subject'] = 'SMTP Test E-Mail'
            
            body = "Dies ist eine Test-E-Mail vom Asset Management System (direkter SMTP-Test)."
            msg.attach(MIMEText(body, 'plain'))
            
            print("\nSende E-Mail...")
            server.send_message(msg)
            print("E-Mail erfolgreich gesendet!")
            
    except Exception as e:
        print(f"\nFehler aufgetreten:")
        print(f"Typ: {type(e).__name__}")
        print(f"Details: {str(e)}")
        raise
    
    print("\n=== Test abgeschlossen ===")

if __name__ == '__main__':
    test_smtp_connection()
