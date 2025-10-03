from flask import Blueprint

categories_bp = Blueprint('md3_categories', __name__)

from . import routes
