import csv
import io
from app import db
from app.models import Supplier

def import_suppliers_from_csv(csv_file, delimiter=','):
    """
    Importiert Lieferanten aus einer CSV-Datei
    
    Parameter:
        csv_file: FileStorage-Objekt der hochgeladenen CSV-Datei
        delimiter: Trennzeichen in der CSV-Datei (Standard: Komma)
        
    Returns:
        dict: Ergebnis mit Statistiken (importiert, übersprungen, Fehler)
    """
    # Statistiken für den Rückgabewert
    stats = {
        'imported': 0,
        'skipped': 0,
        'errors': [],
        'imported_items': []
    }
    
    # CSV einlesen
    csv_content = csv_file.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
    
    # Feldnamen normalisieren und prüfen
    if not reader.fieldnames:
        stats['errors'].append('Die CSV-Datei ist leer oder hat ein ungültiges Format')
        return stats
        
    field_names = [field.lower().strip() for field in reader.fieldnames]
    
    # Prüfen, ob Pflichtfelder vorhanden sind
    if 'name' not in field_names:
        stats['errors'].append('Die CSV-Datei enthält keine Spalte "Name"')
        return stats
    
    # Mapping von CSV-Spalten zu Datenbankfeldern
    field_mapping = {
        'name': 'name',
        'adresse': 'address',
        'address': 'address',
        'anschrift': 'address',
        'telefon': 'phone',
        'phone': 'phone',
        'tel': 'phone',
        'telefonnummer': 'phone',
        'e-mail': 'email',
        'email': 'email',
        'mail': 'email',
        'webseite': 'website',
        'website': 'website',
        'kundennummer': 'customer_number',
        'customer_number': 'customer_number',
        'kreditornummer': 'creditor_number',
        'creditor_number': 'creditor_number',
        'beschreibung': 'description',
        'description': 'description',
        'notizen': 'description',
        'notes': 'description',
        'kontaktinfo': 'contact_info',
        'contact_info': 'contact_info',
        'kontaktinformation': 'contact_info',
        'ansprechpartner': 'contact_info'
    }
    
    # CSV-Zeilen verarbeiten
    for row in reader:
        try:
            # Neuen Supplier vorbereiten
            supplier_data = {}
            
            # Werte aus CSV zuweisen
            for csv_field, value in row.items():
                csv_field_lower = csv_field.lower().strip()
                
                if csv_field_lower in field_mapping:
                    db_field = field_mapping[csv_field_lower]
                    supplier_data[db_field] = value.strip() if value else None
            
            # Prüfen ob Name vorhanden ist
            if not supplier_data.get('name'):
                stats['skipped'] += 1
                stats['errors'].append(f"Zeile übersprungen: Kein Name angegeben")
                continue
                
            # Prüfen ob Lieferant bereits existiert
            existing_supplier = Supplier.query.filter_by(name=supplier_data['name']).first()
            if existing_supplier:
                # Vorhandenen Lieferanten aktualisieren
                for key, value in supplier_data.items():
                    if key != 'name':  # Name bleibt unverändert
                        setattr(existing_supplier, key, value)
                db.session.commit()
                stats['skipped'] += 1
                stats['errors'].append(f"Lieferant '{supplier_data['name']}' existiert bereits und wurde aktualisiert")
                continue
            
            # Neuen Lieferanten erstellen
            new_supplier = Supplier(**supplier_data)
            db.session.add(new_supplier)
            db.session.flush()  # Um die ID zu erhalten
            
            stats['imported'] += 1
            stats['imported_items'].append(new_supplier)
            
        except Exception as e:
            stats['errors'].append(f"Fehler beim Import: {str(e)}")
            stats['skipped'] += 1
            db.session.rollback()
    
    # Änderungen speichern
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        stats['errors'].append(f"Fehler beim Speichern der Änderungen: {str(e)}")
    
    return stats
