from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from .models import Asset, db, Loan, Document, CostEntry, InventorySession, InventoryItem, InventoryTeam
from .forms import AssetForm, LoanForm, DocumentForm, CostEntryForm, InventorySessionForm, InventoryTeamForm, InventoryCheckForm
import csv
from io import StringIO, BytesIO
from datetime import datetime, timedelta
import qrcode
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
import io
from sqlalchemy import func, or_
from dateutil.relativedelta import relativedelta
from flask_login import login_required, current_user
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from flask import send_file
import tempfile
import os

main = Blueprint('main', __name__)

# Konfiguration für Datei-Uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
def index():
    """Dashboard-Ansicht"""
    # Hole die Assets des Benutzers
    user_assets = Asset.query.all()
    
    # Status-Zähler
    active_count = len([a for a in user_assets if a.status == 'active'])
    on_loan_count = len([a for a in user_assets if a.status == 'on_loan'])
    inactive_count = len([a for a in user_assets if a.status == 'inactive'])
    
    # Wertentwicklung über die letzten 6 Monate
    today = datetime.utcnow()
    months = []
    values = []
    
    # Für jeden Monat die Wertentwicklung berechnen
    for i in range(5, -1, -1):
        date = today.replace(day=1) - relativedelta(months=i)
        next_date = date + relativedelta(months=1)
        months.append(date.strftime('%B %Y'))
        
        # Assets finden, die bis zu diesem Monat erstellt wurden
        month_assets = Asset.query.filter(
            Asset.created_at < next_date
        ).all()
        
        # Gesamtwert für diesen Monat berechnen
        total_value = 0
        for asset in month_assets:
            try:
                if asset.value is not None:
                    total_value += float(asset.value)
            except (ValueError, TypeError):
                print(f"Warnung: Ungültiger Wert für Asset {asset.name}: {asset.value}")
                continue
        
        values.append(total_value)
        print(f"\nMonat {date.strftime('%B %Y')}:")
        print(f"Gefundene Assets: {len(month_assets)}")
        print(f"Gesamtwert: {total_value}")
        for asset in month_assets:
            print(f"- {asset.name}: {asset.value} (Erstellt: {asset.created_at})")
    
    # Kategorien
    category_data = []
    categories = {}
    for asset in user_assets:
        cat = asset.category or 'Ohne Kategorie'
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        category_data.append({
            'category': category,
            'count': count
        })
    
    # Kostenverteilung
    cost_types = {
        'purchase': 'Anschaffung',
        'maintenance': 'Wartung',
        'repair': 'Reparatur',
        'upgrade': 'Upgrade/Erweiterung',
        'insurance': 'Versicherung',
        'other': 'Sonstiges'
    }
    
    costs = {'Anschaffung': 0}  # Initialisiere mit Anschaffungskosten
    # Alle Assets für die Kostenberechnung verwenden
    all_assets = Asset.query.all()
    
    # Erst die Anschaffungskosten (value) der Assets summieren
    for asset in all_assets:
        if asset.value:
            costs['Anschaffung'] += float(asset.value)
    
    # Dann die zusätzlichen Kosteneinträge hinzufügen
    for asset in all_assets:
        if hasattr(asset, 'cost_entries'):
            for entry in asset.cost_entries:
                cost_type = cost_types.get(entry.cost_type, 'Sonstiges')
                if cost_type != 'Anschaffung':  # Vermeide Doppelzählung von Anschaffungskosten
                    costs[cost_type] = costs.get(cost_type, 0) + entry.amount
    
    # Entferne Kostentypen mit 0 Kosten
    costs = {k: v for k, v in costs.items() if v > 0}
    
    cost_type_labels = list(costs.keys())
    cost_amounts = [costs[label] for label in cost_type_labels]
    
    print("\nKostenverteilung:")
    for label, amount in zip(cost_type_labels, cost_amounts):
        print(f"{label}: {amount}")
    
    # Letzte Assets
    recent_assets = Asset.query.order_by(Asset.created_at.desc()).limit(5).all()
    
    return render_template('dashboard.html',
        active_count=active_count,
        on_loan_count=on_loan_count,
        inactive_count=inactive_count,
        months=months,
        values=values,
        category_data=category_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts,
        recent_assets=recent_assets
    )

@main.route('/dashboard')
def dashboard():
    # Hole die letzten 5 Assets des Benutzers
    recent_assets = Asset.query.order_by(Asset.id.desc()).limit(5).all()
    
    # Statistiken für die Charts
    total_assets = Asset.query.count()
    on_loan = Asset.query.filter_by(status='on_loan').count()
    inactive = Asset.query.filter_by(status='inactive').count()
    active = total_assets - on_loan - inactive

    # Debug: Zeige alle Assets und ihre Werte
    print("\nAlle Assets und ihre Werte:")
    all_assets = Asset.query.all()
    for asset in all_assets:
        print(f"Asset: {asset.name}, Wert: {asset.value}, Erstellt am: {asset.created_at}")

    # Wertentwicklung über die letzten 6 Monate
    today = datetime.utcnow()
    months = []
    values = []
    
    print("\nWertentwicklung Berechnung:")
    # Für jeden Monat die Wertentwicklung berechnen
    for i in range(5, -1, -1):
        date = today.replace(day=1) - relativedelta(months=i)
        next_date = date + relativedelta(months=1)
        months.append(date.strftime('%B %Y'))
        
        # Assets finden, die bis zu diesem Monat erstellt wurden
        month_assets = Asset.query.filter(
            Asset.created_at < next_date
        ).all()
        
        # Gesamtwert für diesen Monat berechnen
        total_value = 0
        for asset in month_assets:
            try:
                if asset.value is not None:
                    total_value += float(asset.value)
            except (ValueError, TypeError):
                print(f"Warnung: Ungültiger Wert für Asset {asset.name}: {asset.value}")
                continue
        
        values.append(total_value)
        print(f"\nMonat {date.strftime('%B %Y')}:")
        print(f"Gefundene Assets: {len(month_assets)}")
        print(f"Gesamtwert: {total_value}")
        for asset in month_assets:
            print(f"- {asset.name}: {asset.value} (Erstellt: {asset.created_at})")
        
        print("\nBerechnete Werte:")
        print("Monate:", months)
        print("Werte:", values)

    # Kategorien
    category_data = []
    categories = {}
    for asset in recent_assets:
        cat = asset.category or 'Ohne Kategorie'
        categories[cat] = categories.get(cat, 0) + 1
    
    for category, count in categories.items():
        category_data.append({
            'category': category,
            'count': count
        })
    
    # Kostenverteilung
    cost_types = {
        'purchase': 'Anschaffung',
        'maintenance': 'Wartung',
        'repair': 'Reparatur',
        'upgrade': 'Upgrade/Erweiterung',
        'insurance': 'Versicherung',
        'other': 'Sonstiges'
    }
    
    costs = {'Anschaffung': 0}  # Initialisiere mit Anschaffungskosten
    # Alle Assets für die Kostenberechnung verwenden
    all_assets = Asset.query.all()
    
    # Erst die Anschaffungskosten (value) der Assets summieren
    for asset in all_assets:
        if asset.value:
            costs['Anschaffung'] += float(asset.value)
    
    # Dann die zusätzlichen Kosteneinträge hinzufügen
    for asset in all_assets:
        if hasattr(asset, 'cost_entries'):
            for entry in asset.cost_entries:
                cost_type = cost_types.get(entry.cost_type, 'Sonstiges')
                if cost_type != 'Anschaffung':  # Vermeide Doppelzählung von Anschaffungskosten
                    costs[cost_type] = costs.get(cost_type, 0) + entry.amount
    
    # Entferne Kostentypen mit 0 Kosten
    costs = {k: v for k, v in costs.items() if v > 0}
    
    cost_type_labels = list(costs.keys())
    cost_amounts = list(costs.values())

    # Kategorien-Statistiken
    categories = db.session.query(
        Asset.category, func.count(Asset.id)
    ).group_by(Asset.category).all()
    
    category_data = [{
        'category': cat or 'Ohne Kategorie',
        'count': count
    } for cat, count in categories]

    return render_template('dashboard.html',
        recent_assets=recent_assets,
        active_count=active,
        on_loan_count=on_loan,
        inactive_count=inactive,
        months=months,
        values=values,
        category_data=category_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts
    )

@main.route('/assets')
def assets():
    """Liste aller Assets des aktuellen Benutzers"""
    assets = Asset.query.all()
    return render_template('assets.html', assets=assets)

@main.route('/add_asset', methods=['GET', 'POST'])
def add_asset():
    form = AssetForm()
    doc_form = DocumentForm()
    
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            category=form.category.data,
            value=form.value.data,
            status=form.status.data,
            location=form.location.data,
            serial_number=form.serial_number.data,
            purchase_date=form.purchase_date.data
        )
        db.session.add(asset)
        db.session.commit()
        
        flash('Asset wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('main.edit_asset', id=asset.id))
    
    return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=None, documents=[], is_new=True)

@main.route('/edit_asset/<int:id>', methods=['GET', 'POST'])
def edit_asset(id):
    """Asset bearbeiten"""
    asset = Asset.query.get_or_404(id)
    
    form = AssetForm(obj=asset)
    doc_form = DocumentForm()
    
    if form.validate_on_submit():
        asset.name = form.name.data
        asset.category = form.category.data
        asset.value = form.value.data
        asset.status = form.status.data
        asset.location = form.location.data
        asset.serial_number = form.serial_number.data
        asset.purchase_date = form.purchase_date.data
        db.session.commit()
        flash('Asset wurde erfolgreich aktualisiert.', 'success')
        return redirect(url_for('main.assets'))
    
    documents = Document.query.filter_by(asset_id=id).all()
    return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=asset, documents=documents, is_new=False)

@main.route('/loan_asset/<int:id>', methods=['GET', 'POST'])
def loan_asset(id):
    """Asset ausleihen"""
    asset = Asset.query.get_or_404(id)
    
    if asset.on_loan:
        flash('Dieses Asset ist bereits ausgeliehen.', 'error')
        return redirect(url_for('main.assets'))
    
    form = LoanForm()
    if form.validate_on_submit():
        loan = Loan(
            asset_id=asset.id,
            borrower_name=form.borrower_name.data,
            start_date=form.start_date.data,
            expected_return_date=form.expected_return_date.data,
            notes=form.notes.data
        )
        asset.status = 'on_loan'
        db.session.add(loan)
        db.session.commit()
        flash('Asset wurde erfolgreich ausgeliehen.', 'success')
        return redirect(url_for('main.assets'))
    
    return render_template('loan_asset.html', form=form, asset=asset)

@main.route('/return_asset/<int:id>', methods=['POST'])
def return_asset(id):
    """Asset zurückgeben"""
    asset = Asset.query.get_or_404(id)
    
    if not asset.on_loan:
        flash('Dieses Asset ist nicht ausgeliehen.', 'error')
        return redirect(url_for('main.assets'))
    
    # Finde das aktuelle Ausleih-Objekt
    loan = Loan.query.filter_by(asset_id=id, return_date=None).first()
    if loan:
        loan.return_date = datetime.utcnow()
        asset.status = 'active'
        db.session.commit()
        flash('Asset wurde erfolgreich zurückgegeben.', 'success')
    
    return redirect(url_for('main.assets'))

@main.route('/upload_document/<int:id>', methods=['POST'])
def upload_document(id):
    asset = Asset.query.get_or_404(id)
    
    form = DocumentForm()
    if form.validate_on_submit():
        file = form.file.data
        filename = secure_filename(file.filename)
        
        document = Document(
            title=form.title.data,
            document_type=form.document_type.data,
            filename=filename,
            notes=form.notes.data,
            asset_id=id,
            size=len(file.read())
        )
        
        file.seek(0)  # Zurück zum Anfang der Datei
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        db.session.add(document)
        db.session.commit()
        
        flash('Dokument wurde erfolgreich hochgeladen.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('main.edit_asset', id=id))

@main.route('/download_document/<int:document_id>')
def download_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        document.filename,
        as_attachment=True,
        download_name=f"{document.title}{os.path.splitext(document.filename)[1]}"
    )

@main.route('/preview_document/<int:document_id>')
def preview_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        document.filename,
        as_attachment=False
    )

@main.route('/delete_document/<int:document_id>', methods=['POST'])
def delete_document(document_id):
    document = Document.query.get_or_404(document_id)
    
    asset_id = document.asset_id
    
    # Lösche die Datei
    try:
        os.remove(os.path.join(UPLOAD_FOLDER, document.filename))
    except OSError:
        pass  # Ignoriere Fehler beim Löschen der Datei
    
    # Lösche den Datenbankeintrag
    db.session.delete(document)
    db.session.commit()
    
    flash('Dokument wurde erfolgreich gelöscht.', 'success')
    return redirect(url_for('main.edit_asset', id=asset_id))

@main.route('/assets/<int:id>/delete', methods=['POST'])
def delete_asset(id):
    """Asset und alle verknüpften Daten löschen"""
    asset = Asset.query.filter_by(id=id).first_or_404()
    
    # Lösche alle verknüpften Dokumente
    documents = Document.query.filter_by(asset_id=id).all()
    for doc in documents:
        if doc.filename:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, doc.filename))
            except OSError:
                pass  # Ignoriere Fehler beim Löschen der Datei
        db.session.delete(doc)
    
    # Lösche alle Kosteneinträge und deren Belege
    cost_entries = CostEntry.query.filter_by(asset_id=id).all()
    for entry in cost_entries:
        if entry.receipt_file:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, entry.receipt_file))
            except OSError:
                pass
        db.session.delete(entry)
    
    # Lösche alle Ausleihvorgänge
    loans = Loan.query.filter_by(asset_id=id).all()
    for loan in loans:
        db.session.delete(loan)
    
    # Lösche das Asset selbst
    db.session.delete(asset)
    db.session.commit()
    
    flash('Asset und alle verknüpften Daten wurden erfolgreich gelöscht.', 'success')
    return jsonify({'success': True})

@main.route('/import_assets', methods=['GET', 'POST'])
def import_assets():
    """CSV Import für Assets"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('Keine Datei ausgewählt.', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        if file.filename == '':
            flash('Keine Datei ausgewählt.', 'error')
            return redirect(request.url)
        
        if not file.filename.endswith('.csv'):
            flash('Bitte wählen Sie eine CSV-Datei aus.', 'error')
            return redirect(request.url)
        
        try:
            # Lese die CSV-Datei
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
            # Importiere die Assets
            for row in csv_input:
                asset = Asset(
                    name=row['name'],
                    category=row['category'],
                    value=float(row['value']),
                    status='active'
                )
                db.session.add(asset)
            
            db.session.commit()
            flash('Assets wurden erfolgreich importiert.', 'success')
            return redirect(url_for('main.assets'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Fehler beim Import: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('import_assets.html')

@main.route('/assets/<int:id>/qr')
def asset_qr(id):
    asset = Asset.query.filter_by(id=id).first_or_404()
    
    # QR-Code mit Asset-Informationen generieren
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    
    # Asset-URL und grundlegende Informationen im QR-Code
    data = {
        'id': asset.id,
        'name': asset.name,
        'category': asset.category,
        'location': asset.location
    }
    qr.add_data(str(data))
    qr.make(fit=True)

    # QR-Code als Bild erzeugen
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Bild in BytesIO-Objekt speichern
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    
    return send_file(img_io, mimetype='image/png')

@main.route('/assets/<int:id>/documents', methods=['GET', 'POST'])
def asset_documents(id):
    asset = Asset.query.get_or_404(id)
    
    form = DocumentForm()
    if form.validate_on_submit():
        file = form.file.data
        if file and allowed_file(file.filename):
            # Sichere Dateinamen generieren
            filename = secure_filename(f"receipt_{file.filename}")
            
            # Speichere die Datei
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(file_path)
            
            # Dokument in der Datenbank speichern
            document = Document(
                asset_id=asset.id,
                title=form.title.data,
                document_type=form.document_type.data,
                filename=filename,
                file_path=file_path,
                mime_type=file.content_type,
                size=os.path.getsize(file_path),
                notes=form.notes.data
            )
            
            db.session.add(document)
            db.session.commit()
            
            flash('Dokument wurde erfolgreich hochgeladen.', 'success')
            return redirect(url_for('main.asset_documents', id=asset.id))
        else:
            flash('Ungültiger Dateityp.', 'error')
    
    documents = Document.query.filter_by(asset_id=asset.id).order_by(Document.upload_date.desc()).all()
    return render_template('documents.html', form=form, asset=asset, documents=documents)

@main.route('/assets/<int:id>/costs')
def asset_costs(id):
    """Zeigt die Kosten eines Assets an"""
    asset = Asset.query.get_or_404(id)
    
    form = CostEntryForm()
    cost_entries = CostEntry.query.filter_by(asset_id=id).order_by(CostEntry.date.desc()).all()
    
    return render_template(
        'cost_entries.html',
        asset=asset,
        form=form,
        cost_entries=cost_entries
    )

@main.route('/assets/<int:id>/costs/add', methods=['POST'])
def add_cost_entry(id):
    """Fügt einen neuen Kosteneintrag hinzu"""
    asset = Asset.query.get_or_404(id)
    
    form = CostEntryForm()
    if form.validate_on_submit():
        receipt_file = form.receipt.data
        filename = None
        if receipt_file:
            filename = secure_filename(receipt_file.filename)
            receipt_file.save(os.path.join(UPLOAD_FOLDER, filename))
        
        cost_entry = CostEntry(
            asset_id=id,
            cost_type=form.cost_type.data,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data,
            receipt_file=filename
        )
        db.session.add(cost_entry)
        db.session.commit()
        flash('Kosteneintrag wurde erfolgreich hinzugefügt.', 'success')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'error')
    
    return redirect(url_for('main.asset_costs', id=id))

@main.route('/costs/<int:id>/delete', methods=['POST'])
def delete_cost_entry(id):
    """Löscht einen Kosteneintrag"""
    cost_entry = CostEntry.query.get_or_404(id)
    
    asset_id = cost_entry.asset_id
    
    # Lösche die Belegdatei, falls vorhanden
    if cost_entry.receipt_file:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, cost_entry.receipt_file))
        except OSError:
            pass
    
    db.session.delete(cost_entry)
    db.session.commit()
    flash('Kosteneintrag wurde erfolgreich gelöscht.', 'success')
    return redirect(url_for('main.asset_costs', id=asset_id))

@main.route('/costs/<int:id>/receipt')
def download_receipt(id):
    """Lädt den Beleg eines Kosteneintrags herunter"""
    cost_entry = CostEntry.query.get_or_404(id)
    
    if not cost_entry.receipt_file:
        abort(404)
    
    return send_from_directory(
        UPLOAD_FOLDER,
        cost_entry.receipt_file,
        as_attachment=True,
        download_name=f"Beleg_{cost_entry.date.strftime('%Y%m%d')}_{cost_entry.cost_type}{os.path.splitext(cost_entry.receipt_file)[1]}"
    )

@main.route('/assets/<int:id>')
def asset_details(id):
    asset = Asset.query.get_or_404(id)
    
    documents = Document.query.filter_by(asset_id=id).all()
    return render_template('asset_details.html', asset=asset, documents=documents)

@main.route('/inventory/planning', methods=['GET'])
def inventory_planning():
    """Zeigt die Inventurplanung an"""
    # Hole aktive und geplante Inventuren
    active_sessions = InventorySession.query.filter(
        InventorySession.status.in_(['planned', 'active'])
    ).order_by(InventorySession.start_date).all()
    
    # Hole abgeschlossene Inventuren (die letzten 5)
    completed_sessions = InventorySession.query.filter_by(
        status='completed'
    ).order_by(InventorySession.end_date.desc()).limit(5).all()
    
    return render_template('inventory/planning.html',
        active_sessions=active_sessions,
        completed_sessions=completed_sessions
    )

@main.route('/inventory/planning/new', methods=['GET', 'POST'])
def inventory_planning_new():
    """Neue Inventur planen"""
    form = InventorySessionForm()
    
    if form.validate_on_submit():
        # Konvertiere die Datumswerte zu DateTime mit Standardzeit
        start_date = datetime.combine(form.start_date.data, datetime.min.time())
        end_date = datetime.combine(form.end_date.data, datetime.max.time())
        
        session = InventorySession(
            name=form.name.data,
            start_date=start_date,
            end_date=end_date,
            location=form.location.data,
            notes=form.notes.data,
            status='planned'
        )
        db.session.add(session)
        db.session.commit()
        
        # Automatisch alle Assets am gewählten Standort zur Inventur hinzufügen
        assets = Asset.query.filter_by(location=form.location.data).all()
        for asset in assets:
            item = InventoryItem(
                session_id=session.id,
                asset_id=asset.id,
                expected_location=asset.location
            )
            db.session.add(item)
        
        db.session.commit()
        flash('Inventur wurde erfolgreich geplant.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    
    return render_template('inventory/planning_new.html', form=form)

@main.route('/inventory/planning/<int:id>', methods=['GET', 'POST'])

def inventory_planning_detail(id):
    """Details einer geplanten Inventur"""
    session = InventorySession.query.get_or_404(id)
    
    if request.method == 'POST':
        location = request.form.get('location')
        if location:
            # Alle Assets am ausgewählten Standort zur Inventur hinzufügen
            assets = Asset.query.filter_by(location=location).all()
            for asset in assets:
                # Prüfen ob das Asset bereits in der Inventur ist
                if not InventoryItem.query.filter_by(session_id=id, asset_id=asset.id).first():
                    item = InventoryItem(
                        session_id=id,
                        asset_id=asset.id,
                        expected_quantity=1,
                        expected_location=asset.location,
                        status='pending'
                    )
                    db.session.add(item)
            
            db.session.commit()
            flash(f'Assets vom Standort {location} wurden hinzugefügt.', 'success')
            
    # Alle verfügbaren Standorte für das Dropdown
    locations = db.session.query(Asset.location).distinct().all()
    locations = [loc[0] for loc in locations if loc[0]]  # Leere Standorte ausfiltern
    
    # Aktuelle Items der Inventur
    items = (InventoryItem.query
            .join(Asset)
            .filter(InventoryItem.session_id == id)
            .all())
            
    return render_template('inventory/planning_detail.html',
                         session=session,
                         items=items,
                         locations=locations)

@main.route('/inventory/start', methods=['POST'])

def inventory_start():
    id = request.form.get('id', type=int)
    if not id:
        flash('Ungültige Anfrage.', 'error')
        return redirect(url_for('main.inventory_planning'))
    
    session = InventorySession.query.get_or_404(id)
    if session.status != 'planned':
        flash('Diese Inventur kann nicht gestartet werden.', 'error')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    session.status = 'active'
    db.session.commit()
    
    flash('Inventur wurde gestartet.', 'success')
    return redirect(url_for('main.inventory_execute_session', id=id))

@main.route('/inventory/planning/<int:id>/cancel', methods=['POST'])
def inventory_planning_cancel(id):
    """Bricht eine geplante Inventur ab"""
    session = InventorySession.query.get_or_404(id)
    
    if session.status not in ['planned', 'active']:
        flash('Diese Inventur kann nicht abgebrochen werden.', 'error')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    session.status = 'cancelled'
    db.session.commit()
    flash('Inventur wurde abgebrochen.', 'success')
    return redirect(url_for('main.inventory_planning'))

@main.route('/inventory/execute')

def inventory_execute():
    """Übersicht der aktiven Inventuren zur Durchführung"""
    # Hole alle aktiven Inventuren
    active_sessions = InventorySession.query.filter_by(status='active').all()
    return render_template('inventory/execute.html', active_sessions=active_sessions)

@main.route('/inventory/execute/<int:id>')

def inventory_execute_session(id):
    """Zeigt die Erfassungsansicht einer Inventur"""
    session = InventorySession.query.get_or_404(id)
    
    if session.status != 'active':
        flash('Diese Inventur ist nicht aktiv.', 'warning')
        return redirect(url_for('main.inventory_execute'))
    
    # Alle Items der Inventur mit Asset-Informationen
    items = (InventoryItem.query
            .join(Asset)
            .filter(InventoryItem.session_id == id)
            .order_by(Asset.name)
            .all())
    
    # Statistiken berechnen
    total_items = len(items)
    counted_items = sum(1 for item in items if item.counted_at is not None)
    progress = (counted_items / total_items * 100) if total_items > 0 else 0
    
    return render_template('inventory/execute_session.html',
                         session=session,
                         items=items,
                         progress=progress)

@main.route('/inventory/check_item/<int:item_id>', methods=['GET', 'POST'])

def inventory_check_item(item_id):
    item = InventoryItem.query.get_or_404(item_id)
    session = item.session  

    if request.method == 'POST':
        item.actual_location = request.form.get('actual_location')
        item.counted_quantity = request.form.get('counted_quantity', type=int)
        item.condition = request.form.get('condition')
        item.notes = request.form.get('notes')
        item.counted_at = datetime.utcnow()
        
        # Bildverarbeitung
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                item.image_path = filename

        db.session.commit()
        flash('Asset erfolgreich erfasst.', 'success')
        return redirect(url_for('main.inventory_execute_session', id=session.id))

    return render_template('inventory/check_item.html',
                         item=item,
                         session=session)

@main.route('/inventory/check/item/<int:id>', methods=['GET', 'POST'])

def inventory_item_detail(id):
    """Zeigt und verarbeitet die Detailansicht eines Inventur-Items"""
    item = InventoryItem.query.get_or_404(id)
    
    if request.method == 'POST':
        item.counted_quantity = request.form.get('counted_quantity', type=int)
        item.actual_location = request.form.get('actual_location')
        item.condition = request.form.get('condition')
        item.condition_notes = request.form.get('condition_notes')
        item.counted_by = current_user.username
        item.counted_at = datetime.utcnow()
        
        # Location korrekt?
        item.location_correct = (item.actual_location.lower() == item.expected_location.lower()) if item.actual_location and item.expected_location else False
        
        # Status basierend auf den Eingaben setzen
        if item.counted_quantity == 0:
            item.status = 'missing'
        elif item.condition in ['damaged', 'repair_needed']:
            item.status = 'damaged'
        else:
            item.status = 'found'
            
        # Bild verarbeiten wenn hochgeladen
        if 'image' in request.files:
            file = request.files['image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                item.image_path = filename
        
        db.session.commit()
        flash('Asset wurde erfolgreich erfasst!', 'success')
        return redirect(url_for('main.inventory_execute_session', session_id=item.session_id))
    
    return render_template('inventory/item_detail.html', item=item)

@main.route('/inventory/search', methods=['GET'])

def inventory_search():
    """Suche nach Assets in der Inventur"""
    query = request.args.get('q', '')
    
    if query:
        # Suche in Assets und InventoryItems
        items = (InventoryItem.query
                .join(Asset)
                .filter(or_(
                    Asset.name.ilike(f'%{query}%'),
                    Asset.serial_number.ilike(f'%{query}%'),
                    Asset.category.ilike(f'%{query}%')
                ))
                .all())
    else:
        items = []
    
    return render_template('inventory/search_results.html',
                         items=items,
                         query=query)

@main.route('/inventory/complete/<int:id>', methods=['POST'])
def complete_inventory(id):
    """Schließt eine Inventur ab"""
    session = InventorySession.query.get_or_404(id)
    
    # Prüfe ob alle Items gezählt wurden
    uncounted_items = InventoryItem.query.filter_by(session_id=id, counted_quantity=None).count()
    if uncounted_items > 0:
        flash(f'Es gibt noch {uncounted_items} ungezählte Assets in dieser Inventur.', 'warning')
        return redirect(url_for('main.inventory_execute'))
    
    # Setze Status auf completed
    session.status = 'completed'
    session.end_date = datetime.utcnow()
    db.session.commit()
    
    flash('Inventur wurde erfolgreich abgeschlossen!', 'success')
    return redirect(url_for('main.inventory_execute'))

@main.route('/uploads/<filename>')
def uploaded_file(filename):
    """Zeigt ein hochgeladenes Bild an"""
    return send_from_directory(UPLOAD_FOLDER, filename)

@main.route('/inventory/planning/add_items/<int:id>', methods=['GET', 'POST'])

def inventory_planning_add_items(id):
    """Fügt Assets zu einer Inventur hinzu"""
    session = InventorySession.query.get_or_404(id)
    
    if request.method == 'POST':
        asset_ids = request.form.getlist('assets')
        for asset_id in asset_ids:
            # Prüfen ob das Asset bereits in der Inventur ist
            if not InventoryItem.query.filter_by(session_id=id, asset_id=asset_id).first():
                item = InventoryItem(
                    session_id=id,
                    asset_id=asset_id,
                    status='pending'
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Assets wurden zur Inventur hinzugefügt.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    # Alle Assets holen, die noch nicht in der Inventur sind
    existing_asset_ids = [item.asset_id for item in session.items]
    available_assets = Asset.query.filter(~Asset.id.in_(existing_asset_ids)).all()
    
    return render_template('inventory/add_items.html',
                         session=session,
                         assets=available_assets)

@main.route('/inventory/reports')

def inventory_reports():
    """Zeigt eine Übersicht aller abgeschlossenen Inventuren mit Berichten"""
    completed_sessions = InventorySession.query.filter_by(status='completed').order_by(InventorySession.end_date.desc()).all()
    return render_template('inventory/reports.html', completed_sessions=completed_sessions)

@main.route('/inventory/reports/<int:id>')

def inventory_report_detail(id):
    """Zeigt detaillierte Informationen zu einer abgeschlossenen Inventur"""
    session = InventorySession.query.get_or_404(id)
    if session.status != 'completed':
        flash('Diese Inventur ist noch nicht abgeschlossen.', 'warning')
        return redirect(url_for('main.inventory_reports'))
    return render_template('inventory/report_detail.html', session=session)

@main.route('/inventory/reports/<int:id>/export')

def inventory_report_export(id):
    """Exportiert einen Inventurbericht als PDF"""
    session = InventorySession.query.get_or_404(id)
    if session.status != 'completed':
        flash('Diese Inventur ist noch nicht abgeschlossen.', 'warning')
        return redirect(url_for('main.inventory_reports'))
    
    # Erstelle ein temporäres PDF
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as pdf_file:
        # PDF Dokument erstellen
        doc = SimpleDocTemplate(
            pdf_file.name,
            pagesize=A4,
            rightMargin=2.5*cm,
            leftMargin=2.5*cm,
            topMargin=2.5*cm,
            bottomMargin=2.5*cm
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = styles['Heading1']
        heading_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Story (Inhaltselemente)
        story = []
        
        # Titel
        story.append(Paragraph('Inventurbericht', title_style))
        story.append(Paragraph(f'Erstellt am {datetime.now().strftime("%d.%m.%Y")}', normal_style))
        story.append(Spacer(1, 20))
        
        # Allgemeine Informationen
        story.append(Paragraph('Allgemeine Informationen', heading_style))
        info_data = [
            ['Name der Inventur:', session.name],
            ['Standort:', session.location],
            ['Zeitraum:', f'{session.start_date.strftime("%d.%m.%Y")} - {session.end_date.strftime("%d.%m.%Y")}'],
            ['Status:', session.status]
        ]
        info_table = Table(info_data, colWidths=[4*cm, 12*cm])
        info_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(info_table)
        story.append(Spacer(1, 20))
        
        # Zusammenfassung
        story.append(Paragraph('Zusammenfassung', heading_style))
        total = len(session.items)
        found = sum(1 for item in session.items if item.status == 'found')
        missing = sum(1 for item in session.items if item.status == 'missing')
        damaged = sum(1 for item in session.items if item.status == 'damaged')
        
        summary_data = [
            ['Gesamtanzahl Assets:', str(total)],
            ['Gefunden:', f'{found} ({found/total*100:.1f}%)'],
            ['Fehlend:', f'{missing} ({missing/total*100:.1f}%)'],
            ['Beschädigt:', f'{damaged} ({damaged/total*100:.1f}%)']
        ]
        summary_table = Table(summary_data, colWidths=[4*cm, 12*cm])
        summary_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6)
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Asset Liste
        story.append(Paragraph('Detaillierte Asset-Liste', heading_style))
        # Tabellen-Header
        asset_data = [['Asset', 'Status', 'Erfasst am', 'Aktueller Standort', 'Zustand']]
        # Tabellen-Daten
        for item in session.items:
            status_text = {
                'found': 'Gefunden',
                'missing': 'Fehlend',
                'damaged': 'Beschädigt'
            }.get(item.status, item.status)
            
            asset_data.append([
                item.asset.name,
                status_text,
                item.counted_at.strftime('%d.%m.%Y %H:%M') if item.counted_at else '-',
                item.actual_location or '-',
                item.condition or '-'
            ])
        
        # Tabelle erstellen
        asset_table = Table(asset_data, repeatRows=1)
        asset_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
        ]))
        story.append(asset_table)
        story.append(Spacer(1, 30))
        
        # Unterschriftszeilen
        signature_data = [[
            Paragraph('____________________<br/>Unterschrift Inventurleiter', normal_style),
            Paragraph('____________________<br/>Unterschrift Prüfer', normal_style)
        ]]
        signature_table = Table(signature_data, colWidths=[8*cm, 8*cm])
        signature_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(signature_table)
        
        # PDF generieren
        doc.build(story)
        
        # PDF-Datei senden
        response = send_file(
            pdf_file.name,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'Inventurbericht_{session.name}_{datetime.now().strftime("%Y%m%d")}.pdf'
        )
        
        # Eine Funktion definieren, die die temporäre Datei nach dem Senden löscht
        @response.call_on_close
        def cleanup():
            try:
                os.unlink(pdf_file.name)
            except (OSError, PermissionError):
                pass  # Ignoriere Fehler beim Löschen
        
        return response

@main.route('/inventory/history')

def inventory_history():
    """Zeigt die Historie aller Inventuren"""
    sessions = InventorySession.query.order_by(InventorySession.start_date.desc()).all()
    return render_template('inventory/history.html', sessions=sessions)
