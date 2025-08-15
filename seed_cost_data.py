#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Skript zum Hinzufügen von Test-Kostendaten für die Kostenverteilung-Chart
"""

from app import create_app
from app.models import db, CostEntry, Asset
from datetime import datetime
import random

def main():
    app = create_app()
    
    with app.app_context():
        # Prüfen, wie viele Einträge bereits existieren
        existing_count = CostEntry.query.count()
        print(f"Vorhandene CostEntry-Einträge: {existing_count}")
        
        # Aktive Assets holen für die Verknüpfung
        assets = Asset.query.filter_by(status='active').limit(10).all()
        
        if not assets:
            print("WARNUNG: Keine aktiven Assets gefunden. Erstelle trotzdem Kostendaten.")
            # Dummy-Asset-ID für den Fall, dass keine Assets vorhanden sind
            asset_ids = [1]
        else:
            asset_ids = [asset.id for asset in assets]
            print(f"Gefundene Asset-IDs für Verknüpfung: {asset_ids}")
        
        # Kostenkategorien, die angezeigt werden sollen
        cost_types = [
            "Anschaffung", 
            "Wartung", 
            "Lizenzen", 
            "Reparatur",
            "Betriebskosten", 
            "Schulung"
        ]
        
        # Testdaten erstellen
        entries_created = 0
        
        for cost_type in cost_types:
            # Pro Kostentyp 2-5 Einträge erstellen
            for _ in range(random.randint(2, 5)):
                # Zufällige Asset-ID aus den verfügbaren auswählen
                asset_id = random.choice(asset_ids)
                
                # Zufälligen Betrag zwischen 100 und 5000 erstellen
                amount = round(random.uniform(100, 5000), 2)
                
                # Kosteneintrag erstellen
                cost_entry = CostEntry(
                    asset_id=asset_id,
                    cost_type=cost_type,
                    amount=amount,
                    description=f"Test {cost_type}",
                    date=datetime.now().date()
                )
                
                db.session.add(cost_entry)
                entries_created += 1
        
        # Änderungen speichern
        db.session.commit()
        print(f"{entries_created} Test-Kosteneinträge erstellt.")
        
        # Überprüfen, ob die Einträge korrekt erstellt wurden
        new_count = CostEntry.query.count()
        print(f"Neue Gesamtanzahl an CostEntry-Einträgen: {new_count}")
        
        # Überprüfen der Verteilung nach Kostentyp
        print("\nVerteilung nach Kostentyp:")
        for cost_type in cost_types:
            count = CostEntry.query.filter_by(cost_type=cost_type).count()
            total = sum(entry.amount for entry in CostEntry.query.filter_by(cost_type=cost_type).all())
            print(f"- {cost_type}: {count} Einträge, Gesamtsumme: {total:.2f} €")

if __name__ == "__main__":
    main()
