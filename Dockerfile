# Basis-Image mit Python
FROM python:3.9-slim

# Arbeitsverzeichnis im Container
WORKDIR /app

# Kopiere alle Dateien in den Container
COPY . .

# Installiere Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Setze Umgebungsvariablen
ENV PYTHONUNBUFFERED=1

# Starte die App über main.py (welches create_app() verwendet)
CMD ["python", "-m", "app.main"]
