#!/bin/bash

# 🚀 Asset Management - Einfaches Setup für Anfänger
# ================================================

echo "🚀 Asset Management Setup für Anfänger"
echo "======================================"

# Prüfen ob wir im richtigen Verzeichnis sind
if [ ! -f "requirements.txt" ]; then
    echo "❌ Fehler: requirements.txt nicht gefunden!"
    echo "📁 Bitte wechseln Sie ins Projekt-Verzeichnis:"
    echo "   cd ~/asset-management"
    exit 1
fi

echo "✅ Projekt gefunden!"

# 1. Virtual Environment aktivieren
echo "🐍 Aktiviere Python-Umgebung..."
source venv/bin/activate

# 2. Abhängigkeiten installieren
echo "📦 Installiere Pakete..."
pip install -r requirements.txt

# 3. Datenbank einrichten
echo "🗄️  Richte Datenbank ein..."
export FLASK_APP=app
flask db upgrade

# 4. Test-Start
echo "🧪 Starte Anwendung für Test..."
echo ""
echo "⏳ Anwendung startet auf http://127.0.0.1:5000"
echo "📱 Öffnen Sie diese Adresse im Browser"
echo "👤 Anmelden mit: admin / admin"
echo ""
echo "🛑 Zum Stoppen: Strg+C drücken"
echo ""

python app/__init__.py
