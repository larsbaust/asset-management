from app import create_app
from app.models import db, Asset, Loan, Document, CostEntry, asset_suppliers, OrderItem, InventoryItem
from datetime import datetime
import os
import shutil
import sys

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
        return True
    except Exception as e:
        print(f"Fehler beim Erstellen des Backups: {e}")
        return False

def reset_assets():
    """Entfernt alle Assets und zugehörige Daten aus der Datenbank"""
    with app.app_context():
        try:
            # Anzahl der Assets vor dem Löschen
            asset_count = Asset.query.count()
            print(f"Anzahl der Assets vor dem Löschen: {asset_count}")

            # 1. Zuerst abhängige Tabellen leeren
            print("Lösche abhängige Daten...")
            
            # 1.1 Inventurdaten entfernen
            inventory_items = InventoryItem.query.all()
            for item in inventory_items:
                db.session.delete(item)
            print(f"Inventurdaten gelöscht")
            
            # 1.2 Leihverhältnisse entfernen
            loans = Loan.query.all()
            for loan in loans:
                db.session.delete(loan)
            print(f"Leihverhältnisse gelöscht")
            
            # 1.3 Dokumente entfernen
            documents = Document.query.filter(Document.asset_id.isnot(None)).all()
            for doc in documents:
                db.session.delete(doc)
            print(f"Asset-Dokumente gelöscht")
            
            # 1.4 Kosteneinträge entfernen
            costs = CostEntry.query.all()
            for cost in costs:
                db.session.delete(cost)
            print(f"Kosteneinträge gelöscht")
            
            # 1.5 Asset-Lieferanten-Zuordnungen entfernen
            db.session.execute(asset_suppliers.delete())
            print("Asset-Lieferanten-Zuordnungen gelöscht")
            
            # 1.6 OrderItems prüfen
            # Wir müssen prüfen, ob asset_id ein Pflichtfeld ist
            # Falls ja, können wir nicht auf NULL setzen
            print("Prüfe OrderItem-Verknüpfungen...")
            try:
                # Versuche, die OrderItems zu identifizieren, die Assets referenzieren
                order_items_with_assets = OrderItem.query.filter(OrderItem.asset_id.isnot(None)).all()
                order_item_count = len(order_items_with_assets)
                
                # Optionen besprechen
                if order_item_count > 0:
                    print(f"HINWEIS: {order_item_count} OrderItems haben Assets-Verknüpfungen, die nicht entfernt werden können.")
                    print("Diese Bestellpositionen bleiben erhalten, aber die referenzierten Assets werden gelöscht.")
            except Exception as e:
                print(f"Fehler beim Prüfen der OrderItems: {e}")
            
            # Commit der Änderungen an abhängigen Tabellen
            db.session.commit()
            
            # 2. Alle Assets einzeln löschen (anstatt bulk delete), um mit Einschränkungen umzugehen
            print("Lösche alle Assets einzeln...")
            assets = Asset.query.all()
            total = len(assets)
            deleted = 0
            
            for asset in assets:
                try:
                    # Asset ID speichern
                    asset_id = asset.id
                    asset_name = asset.name
                    
                    # Asset löschen
                    db.session.delete(asset)
                    db.session.flush()  # Zwischendurch flushen, um Probleme frühzeitig zu erkennen
                    
                    deleted += 1
                    if deleted % 10 == 0 or deleted == total:
                        print(f"Fortschritt: {deleted}/{total} Assets gelöscht")
                        
                except Exception as e:
                    print(f"Fehler beim Löschen von Asset ID {asset_id} ({asset_name}): {e}")
            
            # Änderungen speichern
            db.session.commit()
            
            # Bestätigung
            print("Alle Assets wurden erfolgreich gelöscht!")
            print("Die Datenbank enthält jetzt 0 Assets.")
            
            # Auto-Increment-Wert zurücksetzen
            if db.engine.url.drivername == 'sqlite':
                db.session.execute('DELETE FROM sqlite_sequence WHERE name="asset";')
                db.session.commit()
                print("Asset-ID-Sequenz zurückgesetzt (Neue Assets beginnen wieder bei ID=1)")
            
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Fehler beim Zurücksetzen der Assets: {e}")
            return False

if __name__ == "__main__":
    print("Asset-Datenbank zurücksetzen")
    print("--------------------------")
    print("WARNUNG: Diese Aktion löscht ALLE Assets und dazugehörigen Daten!")
    print("Ein Backup wird automatisch erstellt.")
    print()
    
    # Prüfen, ob im Auto-Modus ausgeführt
    auto_mode = '--auto' in sys.argv
    
    backup_success = backup_database()
    if not backup_success and not auto_mode:
        response = input("Backup fehlgeschlagen. Trotzdem fortfahren? (j/n): ")
        if response.lower() != 'j':
            print("Vorgang abgebrochen.")
            exit()
    elif not backup_success and auto_mode:
        print("Backup fehlgeschlagen, fahre im Auto-Modus trotzdem fort.")
    
    # Bestätigung einholen, außer im Auto-Modus
    proceed = False
    if auto_mode:
        proceed = True
        print("Auto-Modus: Bestätigung übersprungen")
    else:
        confirmation = input("Sind Sie sicher, dass Sie ALLE Assets löschen möchten? (ja/nein): ")
        if confirmation.lower() == 'ja':
            proceed = True
    
    if proceed:
        if reset_assets():
            print()
            print("Zurücksetzen erfolgreich abgeschlossen!")
            print("Alle Assets wurden entfernt, andere Daten (Lieferanten, Standorte, Benutzer) bleiben erhalten.")
        else:
            print("Fehler beim Zurücksetzen der Datenbank.")
    else:
        print("Vorgang abgebrochen.")
