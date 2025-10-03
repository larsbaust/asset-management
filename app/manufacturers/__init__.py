from flask import Blueprint

manufacturers_bp = Blueprint('md3_manufacturers', __name__)

from . import routes
