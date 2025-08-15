"""
API-Blueprints für die Asset-Management-Anwendung
"""

from flask import Blueprint

bp = Blueprint('api', __name__, url_prefix='/api')

# Import von Blueprint-spezifischen Routen
from app.api import calendar_events

# Registriere die Calendar-Events-Blueprint-Routen mit dem api Blueprint
bp.register_blueprint(calendar_events.bp)

# Weitere API-Routes können hier importiert werden
