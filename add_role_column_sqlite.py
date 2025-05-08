import sqlite3

# Pfad zur SQLite-Datenbank anpassen, falls nötig!
db_path = 'instance/app.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE user ADD COLUMN role VARCHAR(20) DEFAULT 'user';")
    print("Spalte 'role' zur Tabelle 'user' hinzugefügt.")
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print("Spalte 'role' existiert bereits.")
    else:
        print("Fehler:", e)

conn.commit()
conn.close()
