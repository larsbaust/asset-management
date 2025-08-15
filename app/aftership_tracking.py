import os
import requests
from dotenv import load_dotenv


load_dotenv()
AFTERSHIP_API_KEY = os.getenv("AFTERSHIP_API_KEY")

def add_tracking_number(tracking_number, slug):
    print("[DEBUG][add_tracking_number] AFTERSHIP_API_KEY:", AFTERSHIP_API_KEY)
    print("[DEBUG][add_tracking_number] Trackingnummer:", tracking_number)
    print("[DEBUG][add_tracking_number] Carrier Slug:", slug)
    """
    Legt eine neue Sendung bei AfterShip an.
    :param tracking_number: Die Paketnummer
    :param slug: AfterShip Carrier-Slug (z.B. "dhl", "dpd-germany")
    :return: Antwort der API als Dictionary
    """
    url = "https://api.aftership.com/v4/trackings"
    headers = {
        "aftership-api-key": AFTERSHIP_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "tracking": {
            "tracking_number": tracking_number,
            "slug": slug
        }
    }
    response = requests.post(url, json=data, headers=headers)
    print("Status:", response.status_code)
    print("Antwort:", response.json())
    return response.json()

def get_tracking_status(tracking_number, slug):
    print("[DEBUG][get_tracking_status] AFTERSHIP_API_KEY:", AFTERSHIP_API_KEY)
    print("[DEBUG][get_tracking_status] Trackingnummer:", tracking_number)
    print("[DEBUG][get_tracking_status] Carrier Slug:", slug)
    """
    Fragt den Sendungsstatus bei AfterShip ab.
    :param tracking_number: Die Paketnummer
    :param slug: AfterShip Carrier-Slug
    :return: Antwort der API als Dictionary
    """
    url = f"https://api.aftership.com/v4/trackings/{slug}/{tracking_number}"
    headers = {
        "aftership-api-key": AFTERSHIP_API_KEY,
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    print("Status:", response.status_code)
    print("Antwort:", response.json())
    return response.json()

def get_all_trackings():
    """
    Ruft alle Sendungen von AfterShip ab und bereitet sie für das Dashboard auf.
    
    Returns:
        dict: Ein Dictionary mit den Lieferungsdaten nach Status gruppiert
              Format: {
                  'in_transit': [{...delivery data...}],
                  'delivered': [{...delivery data...}],
                  'pending': [{...delivery data...}],
                  'counts': {'in_transit': 0, 'delivered': 0, 'pending': 0, 'total': 0},
                  'locations': [{lat: X, lng: Y, status: 'in_transit'},...]
              }
    """
    url = "https://api.aftership.com/v4/trackings"
    headers = {
        "aftership-api-key": AFTERSHIP_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        if 'trackings' not in data['data']:
            print("Keine Sendungen gefunden")
            return {
                'in_transit': [],
                'delivered': [],
                'pending': [],
                'counts': {'in_transit': 0, 'delivered': 0, 'pending': 0, 'total': 0},
                'locations': []
            }
        
        trackings = data['data']['trackings']
        
        # Gruppierung nach Status
        result = {
            'in_transit': [],
            'delivered': [],
            'pending': [],
            'counts': {'in_transit': 0, 'delivered': 0, 'pending': 0, 'total': len(trackings)},
            'locations': []
        }
        
        for tracking in trackings:
            # Status-Mapping: AfterShip -> Dashboard
            tag = tracking.get('tag', '').lower()
            status_category = 'pending'  # Standardwert
            
            if tag in ['delivered', 'delivered_to_sender']:
                status_category = 'delivered'
            elif tag in ['in_transit', 'out_for_delivery', 'info_received']:
                status_category = 'in_transit'
            elif tag in ['exception', 'expired', 'pending']:
                status_category = 'pending'
            
            # Zähler erhöhen
            result['counts'][status_category] += 1
            
            # Sendung zur entsprechenden Kategorie hinzufügen
            result[status_category].append(tracking)
            
            # Wenn Standortdaten vorhanden sind, für die Karte aufbereiten
            if tracking.get('checkpoints') and len(tracking['checkpoints']) > 0:
                last_checkpoint = tracking['checkpoints'][-1]
                if last_checkpoint.get('coordinates'):
                    lat = last_checkpoint['coordinates'].get('lat')
                    lng = last_checkpoint['coordinates'].get('lng')
                    if lat and lng:
                        result['locations'].append({
                            'lat': lat,
                            'lng': lng,
                            'status': status_category,
                            'tracking_number': tracking.get('tracking_number', ''),
                            'carrier': tracking.get('slug', '').upper(),
                            'destination': tracking.get('destination_country_iso3', '')
                        })
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"Fehler beim Abrufen der Sendungen: {e}")
        return {
            'in_transit': [],
            'delivered': [],
            'pending': [],
            'counts': {'in_transit': 0, 'delivered': 0, 'pending': 0, 'total': 0},
            'locations': []
        }

if __name__ == "__main__":
    # Beispiel: DPD Germany
    tracking_number = "01345061273367"
    slug = "dpd-de"
    print("--- Tracking anlegen ---")
    add_tracking_number(tracking_number, slug)
    print("--- Trackingstatus abfragen ---")
    get_tracking_status(tracking_number, slug)
    
    print("--- Alle Sendungen abrufen ---")
    all_trackings = get_all_trackings()
    print(f"Anzahl Sendungen: {all_trackings['counts']['total']}")
    print(f"Davon: In Transit: {all_trackings['counts']['in_transit']}, Geliefert: {all_trackings['counts']['delivered']}, Pending: {all_trackings['counts']['pending']}")
    print(f"Anzahl Standorte für Karte: {len(all_trackings['locations'])}")

