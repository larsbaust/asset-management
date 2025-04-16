from flask import render_template, request
from app.suppliers import suppliers
from app.models import Supplier
from app import db

@suppliers.route('/suppliers')
def supplier_list():
    query = Supplier.query
    search = request.args.get('search', '')
    letter = request.args.get('letter', '')
    if search:
        query = query.filter(Supplier.name.ilike(f"%{search}%"))
    if letter and letter != "Alle":
        query = query.filter(Supplier.name.ilike(f"{letter}%"))
    suppliers_list = query.order_by(Supplier.name).all()
    return render_template('suppliers/list.html', suppliers=suppliers_list, search=search, letter=letter)

@suppliers.route('/suppliers/add')
def supplier_add():
    return "Hier kommt das Formular zum Anlegen eines Lieferanten."
