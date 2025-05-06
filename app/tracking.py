import os
import requests
import json
from dotenv import load_dotenv

# .env laden (nur beim ersten Import nötig)
load_dotenv()

TRACKINGMORE_API_KEY = os.getenv('TRACKINGMORE_API_KEY')
TRACKINGMORE_API_URL = "https://api.trackingmore.com/v4/trackings"


def get_tracking_status(tracking_number, carrier_code):
    """
    Fragt den Status einer Sendung über TrackingMore ab.
    :param tracking_number: Die Paketnummer (z.B. DHL, UPS, GLS)
    :param carrier_code: Der Carrier-Code laut TrackingMore (z.B. 'dhl', 'ups', 'gls')
    :return: Dictionary mit Status-Infos oder None bei Fehler
    """
    headers = {
        "Tracking-Api-Key": TRACKINGMORE_API_KEY,
        "Content-Type": "application/json"
    }
    url = f"{TRACKINGMORE_API_URL}/{carrier_code}/{tracking_number}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        result = response.json()
        print(f"[TrackingMore] FULL API-RESPONSE: {result}")
        if result.get("meta", {}).get("code") == 200 and result.get("data") is not None:
            data = result["data"]
            if isinstance(data, list):
                if len(data) > 0:
                    return data[0]
                else:
                    return None
            return data
        else:
            print(f"API Fehler: {result}")
            return None
    except Exception as e:
        print(f"Fehler bei TrackingMore API: {e}")
        return None


def add_tracking_number(tracking_number, carrier_code):
    """
    Registriert eine Trackingnummer bei TrackingMore.
    Muss einmalig pro Sendung aufgerufen werden, bevor der Status abgefragt werden kann.
    :param tracking_number: Die Paketnummer
    :param carrier_code: Carrier-Code laut TrackingMore
    :return: Antwort der API als Dictionary oder None bei Fehler
    """
    headers = {
        "Tracking-Api-Key": TRACKINGMORE_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "tracking_number": tracking_number,
        "carrier_code": carrier_code
    }
    try:
        response = requests.post(
            "https://api.trackingmore.com/v4/trackings", 
            json=data,
            headers=headers,
            timeout=10
        )
        print("[TrackingMore] add_tracking_number API-Response:", response.text)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        print(f"Fehler beim Hinzufügen der Trackingnummer: {e}")
        if e.response is not None:
            print("[TrackingMore] add_tracking_number API-Fehler-Antwort:", e.response.text)
        return None
    except Exception as e:
        print(f"Sonstiger Fehler: {e}")
        return None

# Beispiel-Aufruf (zum Testen):
# add_tracking_number("00340434161094000001", "dhl")
# status = get_tracking_status("00340434161094000001", "dhl")
# print(status)
