"""
Prüft ob Inventursessions existieren und ob sie Kalender-Events haben
"""
from app import create_app, db
from app.models import InventorySession, CalendarEvent

app = create_app()
with app.app_context():
    print("=" * 70)
    print("INVENTUR-SESSIONS CHECK")
    print("=" * 70)
    
    sessions = InventorySession.query.all()
    print(f"\n{len(sessions)} Inventur-Sessions gefunden:\n")
    
    for session in sessions:
        print(f"ID: {session.id}")
        print(f"  Name:        {session.name}")
        print(f"  Status:      {session.status}")
        print(f"  Start:       {session.start_date}")
        print(f"  Ende:        {session.end_date}")
        print(f"  Standort-ID: {session.location_id}")
        
        # Kalender-Events für diese Session
        events = CalendarEvent.query.filter_by(inventory_session_id=session.id).all()
        print(f"  Events:      {len(events)}")
        
        for event in events:
            print(f"    - Event #{event.id}: {event.title}")
        
        print("-" * 70)
    
    print("\n" + "=" * 70)
