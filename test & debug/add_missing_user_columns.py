import sqlite3

# Pfad zur Datenbankdatei
DB_PATH = "instance/app.db"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

try:
    c.execute("ALTER TABLE user ADD COLUMN failed_logins INTEGER DEFAULT 0;")
    print("Spalte 'failed_logins' hinzugefügt.")
except sqlite3.OperationalError as e:
    print("Fehler oder Spalte existiert schon:", e)

try:
    c.execute("ALTER TABLE user ADD COLUMN lock_until DATETIME;")
    print("Spalte 'lock_until' hinzugefügt.")
except sqlite3.OperationalError as e:
    print("Fehler oder Spalte existiert schon:", e)

conn.commit()
conn.close()
