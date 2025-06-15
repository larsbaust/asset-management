from app import create_app
from app.models import db
from sqlalchemy import text
import os
import shutil
import sys
from datetime import datetime

app = create_app()

def backup_database():
    """Erstellt ein Backup der Datenbank vor dem Zurücksetzen"""
    try:
        # Datenbank-Datei identifizieren (standardmäßig instance/app.db)
        db_path = os.path.join('instance', 'app.db')
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_name = f'db_backup_{timestamp}.db'
        backup_path = os.path.join('backups', backup_name)
        
        # Sicherstellen, dass der Backup-Ordner existiert
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        # Datenbank kopieren
        shutil.copy2(db_path, backup_path)
        print(f"Datenbank-Backup erstellt: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"Fehler beim Erstellen des Backups: {e}")
        return None

def reset_assets_direct(verbose=True):
    """Direkte SQL-Ausführung zum Löschen aller Asset-bezogenen Daten"""
    with app.app_context():
        try:
            if verbose:
                print("Direkte Datenbankmanipulation wird gestartet...")
            
            # Tabellen, die gelöscht werden müssen (in Reihenfolge der Abhängigkeiten)
            tables = [
                'asset_log',           # Asset-Logs
                'inventory_item',      # Inventur-Positionen
                'loan',                # Leihverhältnisse
                'document',            # Dokumente (mit asset_id)
                'cost_entry',          # Kosteneinträge
                'asset_suppliers',     # Asset-Lieferanten (Zuordnungstabelle)
                'asset_manufacturers', # Asset-Hersteller (Zuordnungstabelle)
                'asset',               # Assets selbst
            ]
            
            # Zählen vor dem Löschen
            counts = {}
            for table in tables:
                counts[table] = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if verbose:
                    print(f"- {table}: {counts[table]} Einträge")
            
            # Daten löschen
            if verbose:
                print("\nLösche Daten...")
            deleted_counts = {}
            for table in tables:
                try:
                    if table == 'document':
                        # Bei Dokumenten nur die mit asset_id löschen
                        result = db.session.execute(text("DELETE FROM document WHERE asset_id IS NOT NULL"))
                        deleted_counts[table] = result.rowcount
                    else:
                        # Alle Daten löschen
                        result = db.session.execute(text(f"DELETE FROM {table}"))
                        deleted_counts[table] = result.rowcount
                    if verbose:
                        print(f"- {table}: {deleted_counts[table]} Einträge gelöscht")
                except Exception as e:
                    if verbose:
                        print(f"Fehler beim Löschen von {table}: {e}")
            
            # Auto-Increment-IDs zurücksetzen (SQLite-spezifisch)
            try:
                for table in tables:
                    db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
                if verbose:
                    print("\nAuto-Increment-Sequenzen zurückgesetzt")
            except Exception as e:
                if verbose:
                    print(f"Fehler beim Zurücksetzen der Sequenzen: {e}")
            
            # Änderungen speichern
            db.session.commit()
            if verbose:
                print("\nZurücksetzen erfolgreich abgeschlossen!")
            
            return True, counts, deleted_counts
        except Exception as e:
            db.session.rollback()
            print(f"Fehler beim Zurücksetzen der Datenbank: {e}")
            return False

def reset_orders_direct(verbose=True):
    """Direkte SQL-Ausführung zum Löschen aller Bestellungen"""
    with app.app_context():
        try:
            if verbose:
                print("Lösche alle Bestellungen...")
            
            # Tabellen, die gelöscht werden müssen (in Reihenfolge der Abhängigkeiten)
            tables = [
                'order_item',     # Bestellpositionen
                '"order"',       # Bestellungen selbst - mit Anführungszeichen, da SQL-Reserviertes Wort
            ]
            
            # Zählen vor dem Löschen
            counts = {}
            for table in tables:
                counts[table] = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if verbose:
                    print(f"- {table}: {counts[table]} Einträge")
            
            # Daten löschen
            deleted_counts = {}
            for table in tables:
                try:
                    result = db.session.execute(text(f"DELETE FROM {table}"))
                    deleted_counts[table] = result.rowcount
                    if verbose:
                        print(f"- {table}: {deleted_counts[table]} Einträge gelöscht")
                except Exception as e:
                    if verbose:
                        print(f"Fehler beim Löschen von {table}: {e}")
            
            # Auto-Increment-IDs zurücksetzen
            try:
                for table in tables:
                    db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
                if verbose:
                    print("Auto-Increment-Sequenzen zurückgesetzt")
            except Exception as e:
                if verbose:
                    print(f"Fehler beim Zurücksetzen der Sequenzen: {e}")
            
            # Änderungen speichern
            db.session.commit()
            
            return True, counts, deleted_counts
        except Exception as e:
            db.session.rollback()
            if verbose:
                print(f"Fehler beim Löschen der Bestellungen: {e}")
            return False, {}, {}

def reset_inventory_direct(verbose=True):
    """Direkte SQL-Ausführung zum Löschen aller Inventurberichte"""
    with app.app_context():
        try:
            if verbose:
                print("Lösche alle Inventurberichte...")
            
            # Tabellen, die für Inventur verwendet werden können
            # Hinweis: inventory_item wird bereits bei den Assets behandelt
            # Da inventory_report nicht zu existieren scheint, prüfen wir welche Tabellen existieren
            
            # Leere Liste, da wir aus der Fehlermeldung sehen,
            # dass inventory_report nicht existiert und inventory_item bereits behandelt wird
            tables = []
            
            # Falls keine spezifischen Tabellen für Inventurberichte vorhanden sind
            if not tables:
                if verbose:
                    print("Keine spezifischen Inventurbericht-Tabellen gefunden.")
            
            # Zählen vor dem Löschen
            counts = {}
            for table in tables:
                counts[table] = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                if verbose:
                    print(f"- {table}: {counts[table]} Einträge")
            
            # Daten löschen
            deleted_counts = {}
            for table in tables:
                try:
                    result = db.session.execute(text(f"DELETE FROM {table}"))
                    deleted_counts[table] = result.rowcount
                    if verbose:
                        print(f"- {table}: {deleted_counts[table]} Einträge gelöscht")
                except Exception as e:
                    if verbose:
                        print(f"Fehler beim Löschen von {table}: {e}")
            
            # Auto-Increment-IDs zurücksetzen
            try:
                for table in tables:
                    db.session.execute(text(f"DELETE FROM sqlite_sequence WHERE name='{table}'"))
                if verbose:
                    print("Auto-Increment-Sequenzen zurückgesetzt")
            except Exception as e:
                if verbose:
                    print(f"Fehler beim Zurücksetzen der Sequenzen: {e}")
            
            # Änderungen speichern
            db.session.commit()
            
            return True, counts, deleted_counts
        except Exception as e:
            db.session.rollback()
            if verbose:
                print(f"Fehler beim Löschen der Inventurberichte: {e}")
            return False, {}, {}

def reset_all_data(verbose=True):
    """Löscht alle Assets, Bestellungen und Inventurberichte"""
    results = {
        'assets': {'success': False, 'counts': {}, 'deleted': {}},
        'orders': {'success': False, 'counts': {}, 'deleted': {}},
        'inventory': {'success': False, 'counts': {}, 'deleted': {}}
    }
    
    # 1. Assets zurücksetzen
    try:
        success, counts, deleted = reset_assets_direct(verbose)
        results['assets'] = {'success': success, 'counts': counts, 'deleted': deleted}
    except Exception as e:
        if verbose:
            print(f"Fehler beim Zurücksetzen der Assets: {e}")
    
    # 2. Bestellungen zurücksetzen
    try:
        success, counts, deleted = reset_orders_direct(verbose)
        results['orders'] = {'success': success, 'counts': counts, 'deleted': deleted}
    except Exception as e:
        if verbose:
            print(f"Fehler beim Zurücksetzen der Bestellungen: {e}")
    
    # 3. Inventurberichte zurücksetzen
    try:
        success, counts, deleted = reset_inventory_direct(verbose)
        results['inventory'] = {'success': success, 'counts': counts, 'deleted': deleted}
    except Exception as e:
        if verbose:
            print(f"Fehler beim Zurücksetzen der Inventurberichte: {e}")
    
    # Erfolgsstatus bestimmen - Bei leeren Tabellen (wie inventory) als Erfolg werten
    # Bei Assets und Orders muss es erfolgreich sein
    overall_success = results['assets']['success'] and results['orders']['success']
    
    if verbose:
        if overall_success:
            print("\nAlle Daten wurden erfolgreich zurückgesetzt!")
        else:
            print("\nEs sind Fehler beim Zurücksetzen aufgetreten.")
    
    return overall_success, results

if __name__ == "__main__":
    print("=== Asset-Management-Datenbank zurücksetzen ===")
    print("WARNUNG: Diese Aktion löscht ALLE Assets, Bestellungen und Inventurberichte!")
    print("Diese Methode verwendet direktes SQL und umgeht die ORM-Validierung.")
    print("Lieferanten, Standorte, Benutzer und andere Stammdaten bleiben erhalten.")
    
    # Prüfen, ob Auto-Modus aktiviert ist
    auto_mode = '--auto' in sys.argv
    
    # Backup erstellen
    backup_path = backup_database()
    if backup_path:
        print(f"\nBackup erstellt unter: {backup_path}")
        print("Im Fehlerfall können Sie die Datenbank aus diesem Backup wiederherstellen.")
    else:
        print("\nWARNUNG: Backup konnte nicht erstellt werden!")
        if not auto_mode:
            response = input("Möchten Sie trotzdem fortfahren? (ja/nein): ")
            if response.lower() != 'ja':
                print("Vorgang abgebrochen.")
                exit()
        else:
            print("Auto-Modus: Fahre trotz fehlendem Backup fort.")
    
    # Bestätigung einholen oder überspringen im Auto-Modus
    proceed = False
    if auto_mode:
        proceed = True
        print("\nAuto-Modus: Bestätigung übersprungen")
    else:
        confirmation = input("\nSind Sie absolut sicher, dass Sie ALLE Assets, Bestellungen und Inventurberichte löschen möchten? (ja/nein): ")
        if confirmation.lower() == 'ja':
            proceed = True
    
    if proceed:
        success, results = reset_all_data(verbose=True)
        if success:
            print("\nERFOLG! Alle Daten wurden zurückgesetzt.")
            print("Lieferanten, Standorte, Benutzer und andere Stammdaten bleiben erhalten.")
        else:
            print("\nFehler beim Zurücksetzen der Datenbank.")
    else:
        print("Vorgang abgebrochen.")
