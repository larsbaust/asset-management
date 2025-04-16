#!/bin/bash

echo "Starte Deployment..."

# Ins Projektverzeichnis wechseln
cd ~/asset-management

# Änderungen von GitHub holen
git pull

# Abhängigkeiten installieren/aktualisieren
pip install -r requirements.txt

# App reloaden (über Datei-Touch)
touch ~/asset-management/wsgi.py

echo "Deployment abgeschlossen!"
