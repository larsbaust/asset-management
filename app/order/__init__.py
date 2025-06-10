from flask import Blueprint

order = Blueprint('order', __name__)

from app.order import routes
from app.order import wizard_routes
