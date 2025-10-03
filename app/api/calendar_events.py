"""
API für Kalender-Events
Ermöglicht CRUD-Operationen für Kalender-Events und Erinnerungen
"""

from flask import Blueprint, request, jsonify, current_app, g
from datetime import datetime, timedelta
from app import db
from app.models import CalendarEvent, EventReminder
from app.models import EVENT_TYPE_DELIVERY, EVENT_TYPE_INVENTORY, EVENT_TYPE_MANUAL
from app.models import EVENT_STATUS_PLANNED, EVENT_STATUS_CONFIRMED, EVENT_STATUS_COMPLETED, EVENT_STATUS_CANCELLED
from app.models import REMINDER_STATUS_PENDING, REMINDER_STATUS_DELIVERED, REMINDER_STATUS_READ
# TODO: Implementieren einer Token-Authentifizierung für API-Endpunkte
# from app.api.auth import token_auth
import calendar

bp = Blueprint('calendar_events', __name__, url_prefix='/calendar')


@bp.route('/events', methods=['GET'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def get_events():
    """
    Events für einen bestimmten Monat abrufen
    Query-Parameter:
    - year: Jahr (default: aktuelles Jahr)
    - month: Monat (1-12, default: aktueller Monat)
    """
    # Parameter aus der Anfrage lesen
    year = request.args.get('year', type=int, default=datetime.utcnow().year)
    month = request.args.get('month', type=int, default=datetime.utcnow().month)
    
    # Zeitraum für den angegebenen Monat berechnen
    _, last_day = calendar.monthrange(year, month)
    start_date = datetime(year, month, 1)
    end_date = datetime(year, month, last_day, 23, 59, 59)
    
    # Events aus der Datenbank abfragen
    events = CalendarEvent.query.filter(
        ((CalendarEvent.start_datetime >= start_date) & (CalendarEvent.start_datetime <= end_date)) |
        ((CalendarEvent.end_datetime >= start_date) & (CalendarEvent.end_datetime <= end_date)) |
        ((CalendarEvent.start_datetime <= start_date) & (CalendarEvent.end_datetime >= end_date))
    ).all()
    
    # Events formatieren und zurückgeben
    return jsonify({
        'year': year,
        'month': month,
        'events': [format_event(event) for event in events]
    })


@bp.route('/events', methods=['POST'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def create_event():
    """Neuen Event erstellen"""
    data = request.get_json() or {}
    
    # Pflichtfelder überprüfen
    required_fields = ['title', 'start_datetime', 'event_type']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Pflichtfeld fehlt: {field}'}), 400
    
    # Datumsformate konvertieren
    try:
        data['start_datetime'] = datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00'))
        if 'end_datetime' in data and data['end_datetime']:
            data['end_datetime'] = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return jsonify({'error': 'Ungültiges Datumsformat'}), 400
    
    # Event-Typ überprüfen
    valid_types = [EVENT_TYPE_DELIVERY, EVENT_TYPE_INVENTORY, EVENT_TYPE_MANUAL]
    if data['event_type'] not in valid_types:
        return jsonify({'error': f'Ungültiger Event-Typ. Erlaubte Werte: {", ".join(valid_types)}'}), 400
    
    # Neuen Event erstellen
    event = CalendarEvent(
        title=data['title'],
        description=data.get('description', ''),
        start_datetime=data['start_datetime'],
        end_datetime=data.get('end_datetime'),
        all_day=data.get('all_day', False),
        location=data.get('location', ''),
        event_type=data['event_type'],
        color_token=data.get('color_token'),
        status=data.get('status', EVENT_STATUS_PLANNED),
        order_id=data.get('order_id'),
        inventory_planning_id=data.get('inventory_planning_id'),
        created_by_id=g.current_user.id
    )
    
    db.session.add(event)
    
    # Erinnerungen erstellen, falls vorhanden
    if 'reminders' in data and isinstance(data['reminders'], list):
        for reminder_data in data['reminders']:
            if 'minutes_before' in reminder_data and isinstance(reminder_data['minutes_before'], int):
                remind_at = event.start_datetime - timedelta(minutes=reminder_data['minutes_before'])
                
                reminder = EventReminder(
                    event=event,
                    remind_at=remind_at,
                    user_id=reminder_data.get('user_id', g.current_user.id)
                )
                db.session.add(reminder)
    
    db.session.commit()
    
    return jsonify(format_event(event)), 201


@bp.route('/events/<int:id>', methods=['GET'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def get_event(id):
    """Details für einen bestimmten Event abrufen"""
    event = CalendarEvent.query.get_or_404(id)
    return jsonify(format_event(event))


@bp.route('/events/<int:id>', methods=['PUT'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def update_event(id):
    """Event aktualisieren"""
    event = CalendarEvent.query.get_or_404(id)
    data = request.get_json() or {}
    
    # Daten aktualisieren
    if 'title' in data:
        event.title = data['title']
    if 'description' in data:
        event.description = data['description']
    if 'start_datetime' in data:
        try:
            event.start_datetime = datetime.fromisoformat(data['start_datetime'].replace('Z', '+00:00'))
        except (ValueError, TypeError):
            return jsonify({'error': 'Ungültiges Start-Datum'}), 400
    if 'end_datetime' in data:
        if data['end_datetime']:
            try:
                event.end_datetime = datetime.fromisoformat(data['end_datetime'].replace('Z', '+00:00'))
            except (ValueError, TypeError):
                return jsonify({'error': 'Ungültiges End-Datum'}), 400
        else:
            event.end_datetime = None
    if 'all_day' in data:
        event.all_day = data['all_day']
    if 'location' in data:
        event.location = data['location']
    if 'event_type' in data:
        valid_types = [EVENT_TYPE_DELIVERY, EVENT_TYPE_INVENTORY, EVENT_TYPE_MANUAL]
        if data['event_type'] not in valid_types:
            return jsonify({'error': f'Ungültiger Event-Typ. Erlaubte Werte: {", ".join(valid_types)}'}), 400
        event.event_type = data['event_type']
    if 'color_token' in data:
        event.color_token = data['color_token']
    if 'status' in data:
        valid_status = [EVENT_STATUS_PLANNED, EVENT_STATUS_CONFIRMED, EVENT_STATUS_COMPLETED, EVENT_STATUS_CANCELLED]
        if data['status'] not in valid_status:
            return jsonify({'error': f'Ungültiger Status. Erlaubte Werte: {", ".join(valid_status)}'}), 400
        event.status = data['status']
    if 'order_id' in data:
        event.order_id = data['order_id']
    if 'inventory_planning_id' in data:
        event.inventory_planning_id = data['inventory_planning_id']
    
    # Erinnerungen aktualisieren
    if 'reminders' in data and isinstance(data['reminders'], list):
        # Bestehende Erinnerungen entfernen
        EventReminder.query.filter_by(event_id=event.id).delete()
        
        # Neue Erinnerungen erstellen
        for reminder_data in data['reminders']:
            if 'minutes_before' in reminder_data and isinstance(reminder_data['minutes_before'], int):
                remind_at = event.start_datetime - timedelta(minutes=reminder_data['minutes_before'])
                
                reminder = EventReminder(
                    event=event,
                    remind_at=remind_at,
                    user_id=reminder_data.get('user_id', g.current_user.id)
                )
                db.session.add(reminder)
    
    db.session.commit()
    
    return jsonify(format_event(event))


@bp.route('/events/<int:id>', methods=['DELETE'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def delete_event(id):
    """Event löschen"""
    event = CalendarEvent.query.get_or_404(id)
    
    # Zuerst alle zugehörigen Erinnerungen löschen
    EventReminder.query.filter_by(event_id=event.id).delete()
    
    # Dann den Event löschen
    db.session.delete(event)
    db.session.commit()
    
    return '', 204


@bp.route('/pending-reminders', methods=['GET'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def get_pending_reminders():
    """Ausstehende Erinnerungen für den aktuellen Benutzer abrufen"""
    now = datetime.utcnow()
    
    # Fällige Erinnerungen abfragen (in der Vergangenheit und noch nicht zugestellt)
    reminders = EventReminder.query.join(CalendarEvent).filter(
        EventReminder.user_id == g.current_user.id,
        EventReminder.status == REMINDER_STATUS_PENDING,
        EventReminder.remind_at <= now,
        CalendarEvent.start_datetime >= now  # Nur für zukünftige Events
    ).all()
    
    # Erinnerungen formatieren
    formatted_reminders = []
    for reminder in reminders:
        event = reminder.event
        formatted_reminders.append({
            'id': reminder.id,
            'event_id': event.id,
            'event_title': event.title,
            'event_type': event.event_type,
            'start_datetime': event.start_datetime.isoformat(),
            'remind_at': reminder.remind_at.isoformat()
        })
    
    return jsonify({'reminders': formatted_reminders})


@bp.route('/reminders/<int:id>/read', methods=['POST'])
# @token_auth.login_required  # TODO: Authentifizierung wieder aktivieren
def mark_reminder_as_read(id):
    """Erinnerung als gelesen markieren"""
    reminder = EventReminder.query.get_or_404(id)
    
    # Nur eigene Erinnerungen können als gelesen markiert werden
    if reminder.user_id != g.current_user.id:
        return jsonify({'error': 'Nicht berechtigt'}), 403
    
    reminder.mark_as_read()
    
    return '', 204


# Hilfsfunktionen
def format_event(event):
    """Event für die JSON-Antwort formatieren"""
    formatted = {
        'id': event.id,
        'title': event.title,
        'description': event.description,
        'start_datetime': event.start_datetime.isoformat(),
        'event_type': event.event_type,
        'status': event.status,
        'created_by_id': event.created_by_id
    }
    
    # Optionale Felder hinzufügen, falls vorhanden
    if event.end_datetime:
        formatted['end_datetime'] = event.end_datetime.isoformat()
    if hasattr(event, 'all_day') and event.all_day:
        formatted['all_day'] = event.all_day
    if hasattr(event, 'location') and event.location:
        formatted['location'] = event.location
    if hasattr(event, 'color_token') and event.color_token:
        formatted['color_token'] = event.color_token
    if event.order_id:
        formatted['order_id'] = event.order_id
    if hasattr(event, 'inventory_planning_id') and event.inventory_planning_id:
        formatted['inventory_planning_id'] = event.inventory_planning_id
    
    # Erinnerungen hinzufügen
    formatted['reminders'] = []
    for reminder in event.reminders:
        formatted['reminders'].append({
            'id': reminder.id,
            'remind_at': reminder.remind_at.isoformat(),
            'status': reminder.status,
            'user_id': reminder.user_id
        })
    
    return formatted
