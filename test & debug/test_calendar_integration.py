"""
Test-Skript für die Kalenderintegration
Zeigt alle Kalender-Events an und prüft die Bestellverknüpfung
"""
from app import create_app, db
from app.models import CalendarEvent, Order
from datetime import datetime

app = create_app()
with app.app_context():
    print("=" * 70)
    print("KALENDER-INTEGRATION TEST")
    print("=" * 70)
    
    # Alle Kalender-Events anzeigen
    events = CalendarEvent.query.order_by(CalendarEvent.start_datetime).all()
    print(f"\n[KALENDER] {len(events)} Kalender-Events gefunden:\n")
    
    for event in events:
        print(f"ID: {event.id}")
        print(f"  Titel:        {event.title}")
        print(f"  Beschreibung: {event.description}")
        print(f"  Datum:        {event.start_datetime.strftime('%d.%m.%Y %H:%M')}")
        print(f"  Typ:          {event.event_type}")
        print(f"  Status:       {event.status}")
        
        # Verknüpfte Bestellung
        if event.order_id:
            order = Order.query.get(event.order_id)
            if order:
                print(f"  Bestellung:   #{order.id} ({order.status})")
                if order.supplier:
                    print(f"  Lieferant:    {order.supplier.name}")
        
        print("-" * 70)
    
    # Bestellungen mit Kalender-Events
    orders_with_events = Order.query.filter(Order.expected_delivery_date.isnot(None)).all()
    orders_with_calendar = [o for o in orders_with_events if len(o.calendar_events) > 0]
    
    print(f"\n[BESTELLUNGEN] Bestellungen mit Liefertermin: {len(orders_with_events)}")
    print(f"[KALENDER] Bestellungen mit Kalender-Event: {len(orders_with_calendar)}")
    
    if len(orders_with_events) > len(orders_with_calendar):
        print(f"\n[!] {len(orders_with_events) - len(orders_with_calendar)} Bestellungen haben noch kein Kalender-Event!")
        print("    -> Erstelle neue Bestellung im Wizard um ein Event zu generieren")
    
    print("\n" + "=" * 70)
    print("TEST ABGESCHLOSSEN")
    print("=" * 70)
