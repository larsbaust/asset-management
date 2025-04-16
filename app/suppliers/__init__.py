from flask import Blueprint

suppliers = Blueprint('suppliers', __name__)

from app.suppliers import routes
