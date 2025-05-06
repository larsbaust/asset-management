import os
import requests
from dotenv import load_dotenv


load_dotenv()
AFTERSHIP_API_KEY = os.getenv("AFTERSHIP_API_KEY")

def add_tracking_number(tracking_number, slug):
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

if __name__ == "__main__":
    # Beispiel: DPD Germany
    tracking_number = "01345061273367"
    slug = "dpd-de"
    print("--- Tracking anlegen ---")
    add_tracking_number(tracking_number, slug)
    print("--- Trackingstatus abfragen ---")
    get_tracking_status(tracking_number, slug)
