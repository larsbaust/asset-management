import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen
load_dotenv()

# E-Mail-Konfiguration
MAIL_SERVER = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')

print(f"\nMail-Konfiguration:")
print(f"Server: {MAIL_SERVER}")
print(f"Port: {MAIL_PORT}")
print(f"Benutzername: {MAIL_USERNAME}")
print(f"Passwort-Länge: {len(MAIL_PASSWORD) if MAIL_PASSWORD else 0}")

try:
    print("\nVerbinde mit SMTP-Server...")
    server = smtplib.SMTP_SSL(MAIL_SERVER, MAIL_PORT)
    server.set_debuglevel(1)
    
    print("\nVersuche Login...")
    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    print("Login erfolgreich!")
    
    # Erstelle Test-E-Mail
    msg = MIMEMultipart()
    msg['Subject'] = 'SMTP Test'
    msg['From'] = MAIL_USERNAME
    msg['To'] = MAIL_USERNAME
    
    text = "Dies ist eine Test-E-Mail."
    msg.attach(MIMEText(text, 'plain'))
    
    print("\nSende Test-E-Mail...")
    server.send_message(msg)
    print("E-Mail erfolgreich gesendet!")
    
except Exception as e:
    print(f"\nFehler aufgetreten:")
    print(f"Typ: {type(e).__name__}")
    print(f"Details: {str(e)}")
    
finally:
    try:
        print("\nSchließe Verbindung...")
        server.quit()
        print("Verbindung geschlossen")
    except:
        pass
