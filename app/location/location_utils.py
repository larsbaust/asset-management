import csv
import io
from app import db
from app.models import Location

def import_locations_from_csv(csv_file, delimiter=','):
    """
    Importiert Standorte aus einer CSV-Datei
    
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
        'straße': 'street',
        'strasse': 'street',
        'street': 'street',
        'adresse': 'street',
        'address': 'street',
        'plz': 'postal_code',
        'zip': 'postal_code',
        'postal_code': 'postal_code',
        'postleitzahl': 'postal_code',
        'stadt': 'city',
        'city': 'city',
        'ort': 'city',
        'bundesland': 'state',
        'state': 'state',
        'land': 'state',
        'größe': 'size_sqm',
        'groesse': 'size_sqm',
        'größe_qm': 'size_sqm',
        'groesse_qm': 'size_sqm',
        'size': 'size_sqm',
        'size_sqm': 'size_sqm',
        'fläche': 'size_sqm',
        'flaeche': 'size_sqm',
        'sitzplätze': 'seats',
        'sitzplaetze': 'seats',
        'seats': 'seats',
        'beschreibung': 'description',
        'description': 'description',
        'notizen': 'description',
        'notes': 'description',
        'bild': 'image_url',
        'image': 'image_url',
        'image_url': 'image_url',
        'breitengrad': 'latitude',
        'latitude': 'latitude',
        'längengrad': 'longitude',
        'laengengrad': 'longitude',
        'longitude': 'longitude'
    }
    
    # CSV-Zeilen verarbeiten
    for row in reader:
        try:
            # Neue Location vorbereiten
            location_data = {}
            
            # Werte aus CSV zuweisen
            for csv_field, value in row.items():
                csv_field_lower = csv_field.lower().strip()
                
                if csv_field_lower in field_mapping:
                    db_field = field_mapping[csv_field_lower]
                    location_data[db_field] = value.strip() if value else None
            
            # Prüfen ob Name vorhanden ist
            if not location_data.get('name'):
                stats['skipped'] += 1
                stats['errors'].append(f"Zeile übersprungen: Kein Name angegeben")
                continue
                
            # Prüfen ob Standort bereits existiert
            existing_location = Location.query.filter_by(name=location_data['name']).first()
            if existing_location:
                # Vorhandenen Standort aktualisieren
                for key, value in location_data.items():
                    if key != 'name':  # Name bleibt unverändert
                        setattr(existing_location, key, value)
                db.session.commit()
                stats['skipped'] += 1
                stats['errors'].append(f"Standort '{location_data['name']}' existiert bereits und wurde aktualisiert")
                continue
                
            # Numeric fields conversion
            if location_data.get('size_sqm') and location_data['size_sqm'] is not None:
                try:
                    location_data['size_sqm'] = float(location_data['size_sqm'].replace(',', '.'))
                except (ValueError, TypeError):
                    location_data['size_sqm'] = None
                    stats['errors'].append(f"Ungültige Größe für Standort '{location_data['name']}', auf NULL gesetzt")
            
            if location_data.get('seats') and location_data['seats'] is not None:
                try:
                    location_data['seats'] = int(location_data['seats'])
                except (ValueError, TypeError):
                    location_data['seats'] = None
                    stats['errors'].append(f"Ungültige Sitzplatz-Anzahl für Standort '{location_data['name']}', auf NULL gesetzt")
            
            if location_data.get('latitude') and location_data['latitude'] is not None:
                try:
                    location_data['latitude'] = float(location_data['latitude'].replace(',', '.'))
                except (ValueError, TypeError):
                    location_data['latitude'] = None
                    stats['errors'].append(f"Ungültiger Breitengrad für Standort '{location_data['name']}', auf NULL gesetzt")
                    
            if location_data.get('longitude') and location_data['longitude'] is not None:
                try:
                    location_data['longitude'] = float(location_data['longitude'].replace(',', '.'))
                except (ValueError, TypeError):
                    location_data['longitude'] = None
                    stats['errors'].append(f"Ungültiger Längengrad für Standort '{location_data['name']}', auf NULL gesetzt")
            
            # Neuen Standort erstellen
            new_location = Location(**location_data)
            db.session.add(new_location)
            db.session.flush()  # Um die ID zu erhalten
            
            stats['imported'] += 1
            stats['imported_items'].append(new_location)
            
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
