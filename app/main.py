from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file, current_app, json
from dotenv import load_dotenv
load_dotenv()
from .models import Asset, db, Loan, Document, CostEntry, InventorySession, InventoryItem, InventoryTeam, OrderComment, AssetLog
from .forms import AssetForm, LoanForm, DocumentForm, CostEntryForm, InventorySessionForm, InventoryTeamForm, InventoryCheckForm, MultiLoanForm
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
from .admin import admin_required, permission_required
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from flask import send_file
import tempfile
import os

from app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)


main = Blueprint('main', __name__)

@main.route('/inventory/scan/<int:session_id>/<int:asset_id>', methods=['GET', 'POST'])
def inventory_scan(session_id, asset_id):
    session = InventorySession.query.get_or_404(session_id)
    asset = Asset.query.get_or_404(asset_id)
    item = InventoryItem.query.filter_by(session_id=session.id, asset_id=asset.id).first()
    if not item:
        item = InventoryItem(session_id=session.id, asset_id=asset.id, expected_quantity=1, expected_location=asset.location)
        db.session.add(item)
        db.session.commit()

    if request.method == 'POST':
        item.counted_quantity = int(request.form.get('counted_quantity', 0))
        if 'damaged_quantity' in request.form:
            item.damaged_quantity = int(request.form.get('damaged_quantity', 0))
        item.actual_location = request.form.get('actual_location', '')
        item.condition_notes = request.form.get('notes', '')
        item.counted_by = getattr(request, 'user', None) or "QR-Scan"
        item.counted_at = datetime.now()
        item.status = 'counted'
        db.session.commit()
        flash('Inventur für Asset erfolgreich erfasst!', 'success')
        return redirect(url_for('main.inventory_scan', session_id=session.id, asset_id=asset.id))

    return render_template('inventory_scan.html', asset=asset, inventory_entry=item)

@main.route('/multi_loan', methods=['GET', 'POST'])
@login_required
def multi_loan():
    form = MultiLoanForm()
    if request.method == 'GET':
        asset_ids = request.args.get('asset_ids', '')
        asset_ids = [int(id) for id in asset_ids.split(',')]
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()
        return render_template('multi_loan.html', form=form, assets=assets)

    if form.validate_on_submit():
        from .models import MultiLoan, MultiLoanAsset, Document
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib.units import cm
        import tempfile, base64, os
        from datetime import datetime
        import mimetypes

        # Asset IDs from GET (hidden in form or session)
        asset_ids = request.args.get('asset_ids', '')
        asset_ids = [int(id) for id in asset_ids.split(',') if id]
        assets = Asset.query.filter(Asset.id.in_(asset_ids)).all()

        # Create MultiLoan entry
        multi_loan = MultiLoan(
            borrower_name=form.borrower_name.data,
            start_date=form.start_date.data,
            expected_return_date=form.expected_return_date.data,
            notes=form.notes.data,
            signature=form.signature.data,
            signature_employer=form.signature_employer.data,
            created_at=datetime.utcnow(),
        )
        db.session.add(multi_loan)
        db.session.flush()  # get multi_loan.id
        # Link assets
        for asset in assets:
            mla = MultiLoanAsset(multi_loan_id=multi_loan.id, asset_id=asset.id)
            db.session.add(mla)
            asset.status = 'on_loan'
        db.session.flush()

        # Generate PDF with ReportLab
        styles = getSampleStyleSheet()
        normal = styles['Normal']
        title = styles['Title']
        table_data = [["Name", "Artikelnummer", "Seriennummer", "Kategorie"]]
        for asset in assets:
            table_data.append([
                asset.name or '-',
                getattr(asset, 'article_number', '-') or '-',
                getattr(asset, 'serial_number', '-') or '-',
                asset.category.name if getattr(asset, 'category', None) else '-'
            ])
        # Get a temp filename, then close the file before writing
        tmp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        tmp_pdf_name = tmp_pdf.name
        tmp_pdf.close()  # Ensure file is closed before ReportLab writes
        doc = SimpleDocTemplate(tmp_pdf_name, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        story = []
        # Überschrift
        story.append(Paragraph(f"<b>Übergabeprotokoll für Arbeitsmittel an {form.borrower_name.data}</b>", title))
        story.append(Spacer(1, 12))
        # Für jedes Asset: eigene Tabelle und Rechtstext
        for idx, asset in enumerate(assets, 1):
            asset_table = [
                [Paragraph('<b>Typenbezeichnung</b>', normal), asset.name or '-'],
                [Paragraph('<b>Hersteller</b>', normal), ', '.join([m.name for m in getattr(asset, 'manufacturers', [])]) or '-'],
                [Paragraph('<b>Artikelnummer</b>', normal), getattr(asset, 'article_number', '-') or '-'],
                [Paragraph('<b>Seriennummer</b>', normal), getattr(asset, 'serial_number', '-') or '-'],
                [Paragraph('<b>Kategorie</b>', normal), asset.category.name if getattr(asset, 'category', None) else '-'],
            ]
            story.append(Paragraph(f"§ 1    Die Firma stellt dem Arbeitnehmer das im Folgenden näher bezeichnete Arbeitsmittel zur Verfügung.", normal))
            t = Table(asset_table, colWidths=[5*cm, 10*cm])
            t.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 0.5, '#888888'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
        # Rechtstext mit Paragraphen wie im Screenshot, mit Zeilenabstand
        story.append(Paragraph("§ 2    Das Arbeitsmittel ist vom Arbeitnehmer ausschließlich im Rahmen seiner Tätigkeit zu benutzen. Eine Nutzung für private Zwecke ist nicht gestattet.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 3    Der Arbeitnehmer hat dafür Sorge zu tragen, dass Schäden, die am Gerät auftreten, unverzüglich dem Unternehmen gemeldet werden.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 4    Schäden, die auf normalen Verschleiß zurückzuführen sind, werden auf Kosten der Firma beseitigt. Bei Schäden, die auf unsachgemäßen Gebrauch zurückzuführen sind, behält sich der Arbeitgeber vor, diese auf Kosten des Arbeitnehmers beseitigen zu lassen.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 5    Der Arbeitnehmer ist nicht berechtigt, Arbeitsmittel Dritten zu überlassen oder Zugang zu gewähren.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 6    Der Arbeitnehmer bestätigt mit seiner Unterschrift unter diese Vereinbarung, dass er die Arbeitsmittel von der Firma in funktionsfähigem und mängelfreiem Zustand erhalten hat.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 7    Endet das Arbeitsverhältnis, hat der Arbeitnehmer die Arbeitsmittel unaufgefordert zurückzugeben. Auch während des Bestands des Arbeitsverhältnisses hat der Arbeitnehmer einer Rückgabeaufforderung durch die Firma unverzüglich Folge zu leisten. Zurückbehaltungsrecht steht dem Arbeitnehmer nicht zu. Sollte das Arbeitsmittel mit einem Passwort geschützt sein und der Arbeitnehmer dieses vor dem Arbeitgeber nicht mitteilen, so dass das Passwort nicht mehr nutzbar ist und das Gerät in Folge dessen nicht mehr nutzbar sein, behalten wir uns vor die Kosten einer Reparatur oder einer Neuanschaffung dem Arbeitnehmer in Rechnung zu stellen.", normal))
        story.append(Spacer(1, 6))
        story.append(Paragraph("§ 8    Diese Vereinbarung ist wesentlicher Bestandteil des Arbeitsvertrags. Änderungen und Ergänzungen dieser Vereinbarung bedürfen der Schriftform. Ein Verzicht auf die Schriftform ist nur wirksam, wenn dies schriftlich vereinbart wird. Eine Nichtbeachtung führt zur Unwirksamkeit entsprechender Regelungen. Ausgenommen hiervon sind Individualvereinbarungen i. S. d. § 305 b BGB. Ergänzend zu dieser Vereinbarung gelten die allgemeinen gesetzlichen Bestimmungen. Sollte eine Vorschrift dieser Vereinbarung unwirksam sein, so hat dies nicht die Unwirksamkeit der gesamten Vereinbarung zur Folge.", normal))
        story.append(Spacer(1, 18))
        # Notizen und Datum
        if form.notes.data:
            story.append(Paragraph(f"<b>Notizen:</b> {form.notes.data}", normal))
        story.append(Paragraph(f"Ausleihdatum: {form.start_date.data.strftime('%d.%m.%Y')}", normal))
        if form.expected_return_date.data:
            story.append(Paragraph(f"Erwartetes Rückgabedatum: {form.expected_return_date.data.strftime('%d.%m.%Y')}", normal))
        story.append(Spacer(1, 18))
        # Unterschriftenbereich direkt nach Tabellen & Notizen
        sig_labels = [
            Paragraph('Unterschrift Arbeitgeber:', normal),
            Paragraph('Unterschrift Arbeitnehmer:', normal)
        ]
        sig_imgs = []
        # Arbeitgeber-Signatur
        if form.signature_employer.data and form.signature_employer.data.startswith('data:image'):
            import base64, io
            from reportlab.platypus import Image
            header, encoded = form.signature_employer.data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            img_io = io.BytesIO(img_bytes)
            sig_imgs.append(Image(img_io, width=6*cm, height=2*cm))
        else:
            sig_imgs.append(Spacer(1, 2*cm))
        # Arbeitnehmer-Signatur
        if form.signature.data and form.signature.data.startswith('data:image'):
            import base64, io
            from reportlab.platypus import Image
            header, encoded = form.signature.data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            img_io = io.BytesIO(img_bytes)
            sig_imgs.append(Image(img_io, width=6*cm, height=2*cm))
        else:
            sig_imgs.append(Spacer(1, 2*cm))
        sig_table = Table([
            sig_labels,
            sig_imgs
        ], colWidths=[8*cm, 8*cm])
        sig_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(sig_table)
        doc.build(story)
        pdf_filename = f"multi_loan_{multi_loan.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        pdf_path = os.path.join(uploads_dir, pdf_filename)
        # Move temp file to uploads dir
        os.replace(tmp_pdf_name, pdf_path)
        multi_loan.pdf_filename = pdf_filename
        multi_loan.pdf_path = pdf_path
        db.session.flush()
        # Create Document entry for each asset
        for asset in assets:
            doc_entry = Document(
                asset_id=asset.id,
                title=f"Übergabeprotokoll Sammelausleihe #{multi_loan.id}",
                document_type="handover_protocol",
                filename=pdf_filename,
                file_path=pdf_path,
                mime_type="application/pdf",
                size=os.path.getsize(pdf_path),
                notes=f"Automatisch generiert für Sammelausleihe am {form.start_date.data.strftime('%d.%m.%Y')}",
                upload_date=datetime.utcnow()
            )
            db.session.add(doc_entry)
        db.session.commit()
        flash('Sammelausleihe erfolgreich durchgeführt und Protokoll erstellt!', 'success')
        return redirect(url_for('main.assets'))

    return render_template('multi_loan.html', form=form)

@main.route('/locations')
def locations():
    from .models import Location
    locations = Location.query.order_by(Location.name).all()
    return render_template('locations.html', locations=locations)

@main.route('/locations/add', methods=['GET', 'POST'])
def add_location():
    from .models import Location, db
    from .forms import LocationForm
    form = LocationForm()
    if form.validate_on_submit():
        image_url = None
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_folder = os.path.join(current_app.root_path, 'static', 'location_images')
            os.makedirs(image_folder, exist_ok=True)
            image_path = os.path.join(image_folder, filename)
            form.image.data.save(image_path)
            image_url = f'static/location_images/{filename}'
        location = Location(
            name=form.name.data,
            street=form.street.data,
            postal_code=form.postal_code.data,
            city=form.city.data,
            state=form.state.data,
            size_sqm=form.size_sqm.data,
            seats=form.seats.data,
            description=form.description.data,
            image_url=image_url,
            latitude=form.latitude.data,
            longitude=form.longitude.data
        )
        db.session.add(location)
        db.session.commit()
        flash('Standort erfolgreich angelegt.', 'success')
        return redirect(url_for('main.locations'))
    return render_template('location_form.html', form=form)

@main.route('/locations/<int:id>')
def location_detail(id):
    from .models import Location, LocationImage, InventorySession, Category, InventoryItem
    from .forms import LocationImageForm
    from sqlalchemy import func
    from collections import defaultdict
    
    location = Location.query.get_or_404(id)
    form = LocationImageForm()
    images = LocationImage.query.filter_by(location_id=id).order_by(LocationImage.upload_date.desc()).all()

    # Asset-Status-Filter
    status = request.args.get('status', 'all')
    if status == 'active':
        filtered_assets = [a for a in location.assets if a.status == 'active']
    elif status == 'inactive':
        filtered_assets = [a for a in location.assets if a.status == 'inactive']
    else:
        filtered_assets = location.assets
    
    # Inventur-Informationen laden
    latest_inventory = InventorySession.query.filter_by(
        location_id=id, 
        status='completed'
    ).order_by(InventorySession.end_date.desc()).first()
    
    # Wenn keine abgeschlossene Inventur existiert, prüfe auf geplante oder laufende
    if not latest_inventory:
        latest_inventory = InventorySession.query.filter_by(
            location_id=id
        ).filter(InventorySession.status.in_(['planned', 'in_progress']))\
        .order_by(InventorySession.start_date.desc()).first()
    
    # Wenn keine Inventur-Informationen im Location-Modell gespeichert sind, aber eine Inventur existiert
    if latest_inventory and not location.last_inventory_date:
        if latest_inventory.status == 'completed':
            location.last_inventory_date = latest_inventory.end_date
            location.inventory_status = 'Abgeschlossen'
        elif latest_inventory.status == 'in_progress':
            location.last_inventory_date = latest_inventory.start_date
            location.inventory_status = 'In Bearbeitung'
        elif latest_inventory.status == 'planned':
            location.inventory_status = 'Geplant'
        db.session.commit()
    
    # Bestand nach Namen gruppieren mit Soll- und Ist-Bestand
    stock_by_name = defaultdict(lambda: {'count': 0, 'value': 0, 'actual_count': 0})
    
    # Soll-Bestand aus Assets berechnen
    for asset in filtered_assets:
        name = asset.name or 'Unbenannt'
        stock_by_name[name]['count'] += 1
        if asset.value is not None:
            stock_by_name[name]['value'] += float(asset.value)  # Stelle sicher, dass es als Float behandelt wird
    
    # Ist-Bestand aus der letzten Inventur ermitteln (falls vorhanden)
    if latest_inventory and latest_inventory.status == 'completed':
        inventory_items = InventoryItem.query.filter_by(session_id=latest_inventory.id).all()
        
        # Gruppiere Inventurelemente nach Asset-Namen
        for item in inventory_items:
            if item.asset and item.asset in filtered_assets:
                name = item.asset.name or 'Unbenannt'
                # Verwende gezählte Menge als Ist-Bestand
                if item.counted_quantity is not None:
                    stock_by_name[name]['actual_count'] += item.counted_quantity
                else:
                    # Wenn keine Zählung erfolgt ist, nehmen wir an, dass der Ist-Bestand dem Soll-Bestand entspricht
                    stock_by_name[name]['actual_count'] += 1
    else:
        # Wenn keine Inventur vorhanden ist, setzen wir den Ist-Bestand gleich dem Soll-Bestand
        for name in stock_by_name:
            stock_by_name[name]['actual_count'] = stock_by_name[name]['count']

    return render_template(
        'location_detail.html', 
        location=location, 
        gallery_form=form, 
        gallery_images=images, 
        filtered_assets=filtered_assets, 
        selected_status=status,
        latest_inventory=latest_inventory,
        stock_by_name=stock_by_name
    )

@main.route('/locations/<int:id>/upload_image', methods=['GET', 'POST'])
def upload_location_image(id):
    from .models import Location, LocationImage, db
    from .forms import LocationImageForm
    from flask_login import current_user
    location = Location.query.get_or_404(id)
    form = LocationImageForm()
    if form.validate_on_submit():
        files = request.files.getlist('file')
        if not files or files[0].filename == '':
            flash('Bitte mindestens eine Datei auswählen.', 'danger')
            return redirect(url_for('main.location_detail', id=location.id))
        folder = os.path.join(current_app.root_path, 'static', 'location_gallery', str(location.id))
        os.makedirs(folder, exist_ok=True)
        uploaded = 0
        for file in files:
            filename = secure_filename(file.filename)
            mimetype = file.mimetype
            file_path = os.path.join(folder, filename)
            file.save(file_path)
            new_image = LocationImage(
                location_id=location.id,
                filename=f'location_gallery/{location.id}/{filename}',
                mimetype=mimetype,
                description=form.description.data,
                comment=form.comment.data,
                uploader=getattr(current_user, 'username', 'Unbekannt')
            )
            db.session.add(new_image)
            uploaded += 1
        db.session.commit()
        flash(f'{uploaded} Datei(en) erfolgreich hochgeladen.', 'success')
        return redirect(url_for('main.location_detail', id=location.id))
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'Fehler im Feld {field}: {error}', 'danger')
    return redirect(url_for('main.location_detail', id=location.id))

@main.route('/locations/<int:id>/edit', methods=['GET', 'POST'])
def edit_location(id):
    from .models import Location, db
    from .forms import LocationForm
    location = Location.query.get_or_404(id)
    form = LocationForm(obj=location)
    if form.validate_on_submit():
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            image_folder = os.path.join(current_app.root_path, 'static', 'location_images')
            os.makedirs(image_folder, exist_ok=True)
            image_path = os.path.join(image_folder, filename)
            form.image.data.save(image_path)
            location.image_url = f'static/location_images/{filename}'
        form.populate_obj(location)
        db.session.commit()
        flash('Standort erfolgreich aktualisiert.', 'success')
        return redirect(url_for('main.location_detail', id=location.id))
    return render_template('location_form.html', form=form, edit=True, location=location)

@main.route('/locations/<int:id>/delete', methods=['POST', 'GET'])
@login_required
@admin_required
def delete_location(id):
    from .models import Location, db
    location = Location.query.get_or_404(id)
    if request.method == 'POST':
        db.session.delete(location)
        db.session.commit()
        flash('Standort gelöscht.', 'success')
        return redirect(url_for('main.locations'))
    return render_template('confirm_delete.html', object=location, type='Standort', back_url=url_for('main.location_detail', id=id))

@main.route('/assignments/add', methods=['POST'])
def add_assignment():
    from .models import Assignment, db
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    if not name:
        return jsonify({'status': 'error', 'message': 'Name ist erforderlich.'}), 400
    # Prüfe auf Duplikate
    if Assignment.query.filter_by(name=name).first():
        return jsonify({'status': 'error', 'message': 'Name existiert bereits.'}), 400
    assignment = Assignment(name=name, description=description)
    db.session.add(assignment)
    db.session.commit()
    return jsonify({'status': 'success', 'id': assignment.id, 'name': assignment.name})

@main.route('/manufacturers/add', methods=['POST'])
def add_manufacturer():
    from .models import Manufacturer, db
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    website = data.get('website')
    contact_info = data.get('contact_info')
    if not name:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    if Manufacturer.query.filter_by(name=name).first():
        return jsonify({'success': False, 'message': 'Name existiert bereits.'}), 400
    manufacturer = Manufacturer(
        name=name,
        description=description,
        website=website,
        contact_info=contact_info
    )
    db.session.add(manufacturer)
    db.session.commit()
    return jsonify({'success': True, 'id': manufacturer.id, 'name': manufacturer.name})

# Bulk-Asset-Delete-Route
@main.route('/assets/bulk_archive', methods=['POST'])
@login_required
@permission_required('archive_asset')
def bulk_archive_assets():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'success': False, 'message': 'Keine IDs übergeben.'}), 400
    try:
        from datetime import datetime
        for asset_id in ids:
            asset = Asset.query.get(asset_id)
            asset.status = 'inactive'
            asset.archived_at = datetime.utcnow()
            log = AssetLog(
                user_id=current_user.id,
                username=current_user.username,
                asset_id=asset.id,
                action='archiviert',
                details=None,
                ip_address=request.remote_addr
            )
            db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Wiederherstellen von archivierten Assets
@main.route('/assets/bulk_restore', methods=['POST'])
@login_required
@permission_required('restore_asset')
def bulk_restore_assets():
    data = request.get_json()
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'success': False, 'message': 'Keine IDs übergeben.'}), 400
    try:
        for asset_id in ids:
            asset = Asset.query.get(asset_id)
            asset.status = 'active'
            asset.archived_at = None
            log = AssetLog(
                user_id=current_user.id,
                username=current_user.username,
                asset_id=asset.id,
                action='wiederhergestellt',
                details=None,
                ip_address=request.remote_addr
            )
            db.session.add(log)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Konfiguration für Datei-Uploads
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@main.route('/')
@login_required
def index():
    # Weiterleitung auf das Dashboard
    return redirect(url_for('main.dashboard'))
    
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
    
    # Standorte für die Karte (wie im dashboard-View)
    from .models import Location
    location_objs = Location.query.filter(Location.latitude.isnot(None), Location.longitude.isnot(None)).all()
    locations = [
        {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'street': loc.street,
            'postal_code': loc.postal_code,
            'city': loc.city,
            'description': loc.description
        }
        for loc in location_objs
    ]

    return render_template('dashboard.html',
        active_count=active_count,
        on_loan_count=on_loan_count,
        inactive_count=inactive_count,
        months=months,
        values=values,
        category_data=category_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts,
        recent_assets=recent_assets,
        locations=locations
    )

@main.route('/dashboard')
@login_required
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
        
        # Gesamtwert für diesen Monat berechnen (acquisition_date bevorzugen, sonst created_at)
        all_assets = Asset.query.all()
        total_value = 0
        for asset in all_assets:
            
            asset_date = getattr(asset, 'purchase_date', None) or asset.created_at
            if asset_date and asset_date < next_date:
                try:
                    if asset.value is not None:
                        total_value += float(asset.value)
                except (ValueError, TypeError):
                    print(f"Warnung: Ungültiger Wert für Asset {asset.name}: {asset.value}")
                    continue
        values.append(total_value)
        
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

    # Kategorien-Statistiken (nur Klartextnamen)
    from .models import Category
    # Zeige alle Kategorien (auch neue/ohne Assets) im Chart, aber zähle nur aktive Assets
    categories = db.session.query(
        Category.name,
        func.count(Asset.id)
    ).outerjoin(Asset, (Asset.category_id == Category.id) & (Asset.status == 'active'))\
     .group_by(Category.id, Category.name)\
     .order_by(Category.name)\
     .all()
    category_data = [{
        'category': cat_name or 'Ohne Kategorie',
        'count': count
    } for cat_name, count in categories]
    # Assets ohne Kategorie ergänzen (nur aktive)
    no_category_count = Asset.query.filter((Asset.category == None) & (Asset.status == 'active')).count()
    if no_category_count:
        category_data.append({'category': 'Ohne Kategorie', 'count': no_category_count})

    # Debug-Ausgabe

    # --- Standort-Lieferstatus-Übersicht für Dashboard ---
    from app.models import Order, Location
    from app.aftership_tracking import get_tracking_status, add_tracking_number

    # Hole alle aktiven Bestellungen mit Trackingnummer und Standort
    active_orders = Order.query.filter(Order.archived == False, Order.tracking_number != None, Order.tracking_number != '', Order.location_id != None).all()
    location_delivery_status = []
    for order in active_orders:
        status_tag = None
        subtag_message = None
        if order.tracking_number and order.tracking_carrier:
            try:
                tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)
            except Exception as e:
                tracking_info = None
                if "404" in str(e):
                    add_tracking_number(order.tracking_number, order.tracking_carrier)
                    try:
                        tracking_info = get_tracking_status(order.tracking_number, order.tracking_carrier)
                    except Exception:
                        tracking_info = None
            if tracking_info and 'data' in tracking_info and 'tracking' in tracking_info['data']:
                status_tag = tracking_info['data']['tracking'].get('tag')
                subtag_message = tracking_info['data']['tracking'].get('subtag_message')
        # Status-Klasse für Farbdot
        def tracking_status_class(tag):
            return {
                'Delivered': 'status-delivered',
                'InTransit': 'status-intransit',
                'OutForDelivery': 'status-intransit',
                'AttemptFail': 'status-problem',
                'Exception': 'status-problem',
                'Expired': 'status-problem',
                'InfoReceived': 'status-intransit',
            }.get(tag, 'status-unknown')
        status_class = tracking_status_class(status_tag)
        # Standort-Name
        location_name = order.location_obj.name if order.location_obj else (order.location or '-')
        location_delivery_status.append({
            'location': location_name,
            'status_tag': status_tag or 'Unbekannt',
            'status_class': status_class,
            'status_message': subtag_message or '',
        })

    print('Kategorie-Auswertung für Dashboard (nur aktive Assets):')
    for entry in category_data:
        print(entry)

    # Hersteller-Auswertung für Dashboard (nur aktive Assets)
    from .models import Manufacturer
    manufacturer_data = []
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    for manufacturer in manufacturers:
        count = Asset.query.filter(Asset.manufacturers.any(Manufacturer.id == manufacturer.id), Asset.status == 'active').count()
        manufacturer_data.append({'manufacturer': manufacturer.name, 'count': count})
    # Optional: Nur Hersteller mit mindestens einem Asset anzeigen
    manufacturer_data = [m for m in manufacturer_data if m['count'] > 0]
    print('Hersteller-Auswertung für Dashboard:')
    for entry in manufacturer_data:
        print(entry)

    # Standorte für die Karte (nur mit Koordinaten)
    from .models import Location
    location_objs = Location.query.filter(Location.latitude.isnot(None), Location.longitude.isnot(None)).all()
    locations = [
        {
            'name': loc.name,
            'latitude': loc.latitude,
            'longitude': loc.longitude,
            'street': loc.street,
            'postal_code': loc.postal_code,
            'city': loc.city,
            'description': loc.description
        }
        for loc in location_objs
    ]
    # Robustes chart_data-Objekt für das Dashboard-Template
    chart_data = {
        "status": {
            "active": active if active is not None else 0,
            "on_loan": on_loan if on_loan is not None else 0,
            "inactive": inactive if inactive is not None else 0,
        },
        "costs": {
            "labels": cost_type_labels if cost_type_labels is not None else [],
            "amounts": cost_amounts if cost_amounts is not None else [],
        },
        "value_development": {
            "months": months if months is not None else [],
            "values": values if values is not None else [],
        },
        "categories": category_data if category_data is not None else [],
    }
    # Fallback: assignment_data, falls oben nicht definiert
    if 'assignment_data' not in locals():
        assignment_data = []
    return render_template('dashboard.html',
        recent_assets=recent_assets,
        chart_data=chart_data,
        active_count=active,
        on_loan_count=on_loan,
        inactive_count=inactive,
        months=months,
        values=values,
        category_data=category_data,
        assignment_data=assignment_data,
        cost_type_labels=cost_type_labels,
        cost_amounts=cost_amounts,
        locations=locations,
        manufacturer_data=manufacturer_data,
        location_delivery_status=location_delivery_status
    )

# Route für die Massenarchivierung von Assets
@main.route('/bulk_archive', methods=['POST'])
@login_required
@permission_required('archive_asset')
def bulk_archive():
    try:
        data = request.json
        asset_ids = data.get('asset_ids', [])
        
        if not asset_ids:
            return jsonify({'success': False, 'error': 'Keine Assets ausgewählt'})
            
        # Archivierung durchführen (auf inaktiv setzen)
        count = 0
        errors = []
        for asset_id in asset_ids:
            try:
                # Versuchen, asset_id als Integer zu konvertieren
                asset_id = int(asset_id)
                asset = Asset.query.get(asset_id)
                if asset is None:
                    errors.append(f"Asset mit ID {asset_id} nicht gefunden")
                    continue
                    
                if asset.status == 'active':
                    asset.status = 'inactive'
                    count += 1
            except ValueError:
                errors.append(f"Ungültige Asset-ID: {asset_id}")
            except Exception as inner_e:
                errors.append(f"Fehler bei Asset {asset_id}: {str(inner_e)}")
        
        db.session.commit()
        
        result = {'success': True, 'count': count}
        if errors:
            result['warnings'] = errors
            
        return jsonify(result)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


# Route für die Massenwiederherstellung von Assets
@main.route('/bulk_restore', methods=['POST'])
@login_required
@permission_required('restore_asset')
def bulk_restore():
    try:
        data = request.json
        asset_ids = data.get('asset_ids', [])
        
        if not asset_ids:
            return jsonify({'success': False, 'error': 'Keine Assets ausgewählt'})
            
        # Wiederherstellung durchführen (auf aktiv setzen)
        count = 0
        errors = []
        for asset_id in asset_ids:
            try:
                # Versuchen, asset_id als Integer zu konvertieren
                asset_id = int(asset_id)
                asset = Asset.query.get(asset_id)
                if asset is None:
                    errors.append(f"Asset mit ID {asset_id} nicht gefunden")
                    continue
                    
                if asset.status == 'inactive':
                    asset.status = 'active'
                    count += 1
            except ValueError:
                errors.append(f"Ungültige Asset-ID: {asset_id}")
            except Exception as inner_e:
                errors.append(f"Fehler bei Asset {asset_id}: {str(inner_e)}")
        
        db.session.commit()
        
        result = {'success': True, 'count': count}
        if errors:
            result['warnings'] = errors
            
        return jsonify(result)
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@main.route('/assets')
def assets():
    """Asset-Übersicht mit Filterfunktion"""
    from .models import Assignment, Manufacturer, Supplier
    from collections import defaultdict
    query = Asset.query

    # Filter: Name (Textfeld)
    name = request.args.get('name', '').strip()
    if name:
        query = query.filter(Asset.name.ilike(f"%{name}%"))

    # Filter: Kategorie (Dropdown)
    category = request.args.get('category', '')
    if category not in ('', '0', 0, None):
        query = query.filter(Asset.category_id == int(category))

    # Filter: Standort (Dropdown)
    location = request.args.get('location', '')
    if location not in ('', '0', 0, None):
        query = query.filter(Asset.location_id == int(location))

    # Filter: Hersteller (Dropdown)
    manufacturer_id = request.args.get('manufacturer', '')
    if manufacturer_id not in ('', '0', 0, None):
        query = query.filter(Asset.manufacturers.any(Manufacturer.id == int(manufacturer_id)))

    # Filter: Lieferant (Dropdown)
    supplier_id = request.args.get('supplier', '')
    if supplier_id not in ('', '0', 0, None):
        query = query.filter(Asset.suppliers.any(Supplier.id == int(supplier_id)))

    # Filter: Zuordnung (Dropdown)
    assignment_id = request.args.get('assignment', '')
    if assignment_id not in ('', '0', 0, None):
        query = query.filter(Asset.assignments.any(Assignment.id == int(assignment_id)))

    # Filter: Status (Dropdown)
    status = request.args.get('status', '')
    if status and status != 'all':
        if status == 'active':
            query = query.filter(Asset.status.in_(['active', 'on_loan']))
        else:
            query = query.filter(Asset.status == status)
    elif not status:
        query = query.filter(Asset.status.in_(['active', 'on_loan']))

    # Filter: Nur mit Bild (Checkbox)
    with_image = request.args.get('with_image', '')
    if with_image:
        query = query.filter(Asset.image_url != None)
        
    # Gruppierung aktivieren/deaktivieren
    group_duplicates = request.args.get('group_duplicates', 'true') == 'true'
    
    assets = query.all()
    
    # Gruppierung von Duplikaten nach Name, Artikelnummer und Kategorie
    grouped_assets = []
    if group_duplicates:
        # Dictionary für die Gruppierung erstellen
        groups = defaultdict(list)
        
        # Gruppierungsschlüssel erstellen und Assets gruppieren
        for asset in assets:
            # Schlüssel aus Name, Artikelnummer, Kategorie-ID und Standort-ID
            key = (asset.name, asset.article_number or '', asset.category_id or 0, asset.location_id or 0)
            groups[key].append(asset)
        
        # Gruppierte Assets verarbeiten
        for key, asset_group in groups.items():
            if len(asset_group) > 1:
                # Mehrere Assets mit gleichen Schlüsseln gefunden
                representative = asset_group[0]  # Repräsentatives Asset für die Gruppe
                representative.is_group = True
                representative.group_count = len(asset_group)
                representative.group_ids = [a.id for a in asset_group]
                representative.group_total_value = sum(a.value or 0 for a in asset_group)
                representative.group_assets = asset_group
                grouped_assets.append(representative)
            else:
                # Einzelnes Asset
                asset_group[0].is_group = False
                asset_group[0].group_count = 1
                asset_group[0].group_ids = [asset_group[0].id]
                asset_group[0].group_total_value = asset_group[0].value or 0
                asset_group[0].group_assets = asset_group
                grouped_assets.append(asset_group[0])
    else:
        # Keine Gruppierung, alle Assets einzeln anzeigen
        for asset in assets:
            asset.is_group = False
            asset.group_count = 1
            asset.group_ids = [asset.id]
            asset.group_total_value = asset.value or 0
            asset.group_assets = [asset]
            grouped_assets.append(asset)

    # AssetForm instanziieren, um auf die Choices zuzugreifen
    form = AssetForm()
    categories = [(c[0], c[1]) for c in form.category.choices if c[0]]
    locations = [(l[0], l[1]) for l in form.location_id.choices if l[0]]
    manufacturers = [(str(m.id), m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()]
    suppliers = [(str(s.id), s.name) for s in Supplier.query.order_by(Supplier.name).all()]
    assignments = [(str(a.id), a.name) for a in Assignment.query.order_by(Assignment.name).all()]

    return render_template(
        'assets.html',
        assets=grouped_assets,
        categories=categories,
        locations=locations,
        manufacturers=manufacturers,
        suppliers=suppliers,
        assignments=assignments,
        group_duplicates=group_duplicates,
        selected={
            'name': name,
            'category': category,
            'location': location,
            'manufacturer': manufacturer_id,
            'supplier': supplier_id,
            'assignment': assignment_id,
            'with_image': with_image,
            'status': status if status else 'active'
        }
    )

@main.route('/categories/add', methods=['POST'])
def add_category():
    from .models import Category
    from . import db
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    if Category.query.filter_by(name=data['name']).first():
        return jsonify({'success': False, 'message': 'Kategorie existiert bereits'}), 400
    category = Category(name=data['name'])
    db.session.add(category)
    try:
        db.session.commit()
        return jsonify({'success': True, 'id': category.id, 'name': category.name})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main.route('/categories/delete', methods=['POST'])
def delete_category():
    from .models import Category
    from . import db
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'message': 'Name ist erforderlich'}), 400
    category = Category.query.filter_by(name=data['name']).first()
    if not category:
        return jsonify({'success': False, 'message': 'Kategorie nicht gefunden'}), 404
    db.session.delete(category)
    try:
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400

@main.route('/add_asset', methods=['GET', 'POST'])
def add_asset():
    from .models import Assignment, Manufacturer, Supplier
    form = AssetForm()
    doc_form = DocumentForm()
    
    if form.validate_on_submit():
        asset = Asset(
            name=form.name.data,
            category_id=int(form.category.data) if form.category.data else None,
            value=form.value.data,
            status=form.status.data,
            location_id=form.location_id.data if form.location_id.data else None,
            article_number=form.article_number.data,
            ean=form.ean.data,
            serial_number=form.serial_number.data,
            purchase_date=form.purchase_date.data
        )
        # IDs als Liste holen (Strings zu int)
        assignment_ids = [int(i) for i in request.form.getlist('assignments')]
        manufacturer_ids = [int(i) for i in request.form.getlist('manufacturers')]
        supplier_ids = [int(i) for i in request.form.getlist('suppliers')]
        # Relationen setzen
        asset.assignments = Assignment.query.filter(Assignment.id.in_(assignment_ids)).all() if assignment_ids else []
        asset.manufacturers = Manufacturer.query.filter(Manufacturer.id.in_(manufacturer_ids)).all() if manufacturer_ids else []
        asset.suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all() if supplier_ids else []
        # Bild-Upload verarbeiten
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            # Eindeutigen Dateinamen erzeugen
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            img_folder = os.path.join(current_app.static_folder, 'images')
            if not os.path.exists(img_folder):
                os.makedirs(img_folder)
            form.image.data.save(os.path.join(img_folder, filename))
            asset.image_url = f"/static/images/{filename}"
        db.session.add(asset)
        db.session.commit()
        # Logging
        log = AssetLog(
            user_id=current_user.id,
            username=current_user.username,
            asset_id=asset.id,
            action='angelegt',
            details=None,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        flash('Asset wurde erfolgreich erstellt.', 'success')
        return redirect(url_for('main.edit_asset', id=asset.id))
    
    return render_template('edit_asset.html', form=form, doc_form=doc_form, asset=None, documents=[], is_new=True)

@main.route('/edit_asset/<int:id>', methods=['GET', 'POST'])
def edit_asset(id):
    from .models import Assignment, Manufacturer, Supplier
    asset = Asset.query.get_or_404(id)
    form = AssetForm(obj=asset)
    doc_form = DocumentForm()
    # Multi-Select-Felder mit aktuellen IDs befüllen
    form.assignments.data = [str(a.id) for a in asset.assignments]
    form.manufacturers.data = [str(m.id) for m in asset.manufacturers]
    form.suppliers.data = [str(s.id) for s in asset.suppliers]
    
    if form.validate_on_submit():
        asset.name = form.name.data
        from .models import Category
        asset.category_id = int(form.category.data) if form.category.data else None
        asset.value = form.value.data
        asset.status = form.status.data
        asset.location_id = int(form.location_id.data) if form.location_id.data else None
        asset.article_number = form.article_number.data
        asset.ean = form.ean.data
        asset.serial_number = form.serial_number.data
        asset.purchase_date = form.purchase_date.data
        # IDs als Liste holen (Strings zu int)
        assignment_ids = request.form.getlist('assignments')
        manufacturer_ids = request.form.getlist('manufacturers')
        supplier_ids = request.form.getlist('suppliers')
        # Relationen setzen (nur wenn IDs übergeben wurden, sonst unverändert lassen)
        if assignment_ids:
            asset.assignments = Assignment.query.filter(Assignment.id.in_(assignment_ids)).all()
        if manufacturer_ids:
            asset.manufacturers = Manufacturer.query.filter(Manufacturer.id.in_(manufacturer_ids)).all()
        if supplier_ids:
            asset.suppliers = Supplier.query.filter(Supplier.id.in_(supplier_ids)).all()
        # Bild-Upload beim Bearbeiten
        if form.image.data:
            filename = secure_filename(form.image.data.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            img_folder = os.path.join(current_app.static_folder, 'images')
            if not os.path.exists(img_folder):
                os.makedirs(img_folder)
            form.image.data.save(os.path.join(img_folder, filename))
            asset.image_url = f"/static/images/{filename}"
        db.session.commit()
        # Logging
        log = AssetLog(
            user_id=current_user.id,
            username=current_user.username,
            asset_id=asset.id,
            action='bearbeitet',
            details=None,
            ip_address=request.remote_addr
        )
        db.session.add(log)
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

        # PDF-Export: Übergabeprotokoll
        from flask import send_file
        from fpdf import FPDF
        import tempfile, base64
        import io
        pdf = FPDF()
        pdf.add_page()
        # Asset-Bild oben rechts einfügen
        asset_img_path = None
        import requests
        import os
        print('[PDF] Asset-Bild Handling startet')
        if getattr(asset, 'image_url', None):
            img_url = asset.image_url
            if img_url.startswith('http://') or img_url.startswith('https://'):
                print(f"[PDF] Lade Bild von externer URL: {img_url}")
                resp = requests.get(img_url, timeout=5)
                if resp.status_code == 200:
                    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                        tmp_img.write(resp.content)
                        tmp_img.flush()
                        asset_img_path = tmp_img.name
            elif img_url.startswith('/static/'):
                static_path = os.path.join(current_app.root_path, img_url.lstrip('/'))
                print(f"[PDF] Lade Bild aus static (relativer Pfad): {static_path}")
                if os.path.exists(static_path):
                    asset_img_path = static_path
            else:
                print(f"[PDF] Unbekanntes Format für asset.image_url: {img_url}")
        elif getattr(asset, 'image', None):
            static_path = os.path.join(current_app.root_path, 'static', 'uploads', asset.image)
            print(f"[PDF] Lade Bild aus Uploads: {static_path}")
            if os.path.exists(static_path):
                asset_img_path = static_path
        else:
            static_path = os.path.join(current_app.root_path, 'static', 'img', 'asset_placeholder.png')
            print(f"[PDF] Lade Platzhalterbild: {static_path}")
            if os.path.exists(static_path):
                asset_img_path = static_path
        print(f"[PDF] Asset-Bild Pfad gewählt: {asset_img_path}")
        if asset_img_path:
            from PIL import Image
            img = Image.open(asset_img_path)
            tmp_img_path = asset_img_path
            print(f"[PDF] Asset-Bild existiert: {asset_img_path}, Format: {img.format}, Größe: {img.size}")
            if img.format not in ['PNG', 'JPEG', 'JPG']:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                    img.save(tmp_img.name, format='PNG')
                    tmp_img.flush()
                    tmp_img_path = tmp_img.name
            print(f"[PDF] Asset-Bild wird eingefügt: {tmp_img_path}")
            # pdf.image(tmp_img_path, x=150, y=25, w=40)  # ENTFERNT: Bild oben rechts
        else:
            print('[PDF] Kein Asset-Bild gefunden oder geladen!')
        pdf.set_font('Arial', 'B', 14)
        pdf.cell(0, 10, f'Übergabeprotokoll für Arbeitsmittel an {form.borrower_name.data}', ln=1, align='C')
        pdf.ln(5)
        pdf.set_font('Arial', '', 11)
        pdf.multi_cell(0, 7, '§ 1 Die Firma stellt dem Arbeitnehmer das im Folgenden näher bezeichnete Arbeitsmittel zur Verfügung.')
        pdf.ln(3)
        # Tabelle mit den gewünschten Feldern (nur einmal!)
        pdf.set_font('Arial', '', 11)
        # Hersteller-Liste vorbereiten (vor Tabelle!)
        hersteller_liste = ''
        if hasattr(asset, 'manufacturers') and asset.manufacturers and len(asset.manufacturers) > 0:
            hersteller_liste = ', '.join([m.name for m in asset.manufacturers if hasattr(m, 'name') and m.name])
        elif getattr(asset, 'article_number', None):
            hersteller_liste = asset.article_number
        else:
            hersteller_liste = '-'
        # Bild links, Tabelle rechts daneben
        y_start = pdf.get_y()
        if asset_img_path:
            from PIL import Image
            img = Image.open(asset_img_path)
            tmp_img_path = asset_img_path
            if img.format not in ['PNG', 'JPEG', 'JPG']:
                with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                    img.save(tmp_img.name, format='PNG')
                    tmp_img.flush()
                    tmp_img_path = tmp_img.name
        # Tabelle mit x-Offset (jetzt weiter links)
        x_table = 15
        # Tabelle wie im Excel-Beispiel: Bild links (rowspan), dann Label/Wert-Zellen
        # Dynamische, saubere Haupttabelle mit Bild (keine doppelte Tabelle mehr)
        img_width = 45
        max_table_width = 180
        label_width = 55
        value_width = max_table_width - img_width - label_width
        pdf.set_xy(x_table + 0, y_start)
        # Werte vorbereiten
        rows = [
            ("Typenbezeichnung:", asset.name or "-"),
            ("Hersteller / Gerätenummer:", hersteller_liste),
            ("Seriennummer:", asset.serial_number or "-"),
            ("Zubehör:", form.notes.data or "-")
        ]
        # Zeilenhöhen dynamisch bestimmen
        pdf.set_font('Arial', '', 12)
        line_heights = []
        for label, value in rows:
            n_lines = max(
                pdf.get_string_width(value) // value_width + 1,
                1
            )
            line_heights.append(6 * n_lines)
        total_height = sum(line_heights)
        # Bildzelle links mit rowspan
        if asset_img_path:
            x_imgcell = pdf.get_x()
            y_imgcell = pdf.get_y()
            pdf.cell(img_width, total_height, '', border=1)
            x_img = x_imgcell + 2
            y_img = y_imgcell + 2
            pdf.image(asset_img_path, x=x_img, y=y_img, w=img_width - 4, h=total_height - 4)
        else:
            pdf.cell(img_width, total_height, '', border=1)
        # Tabellenzeilen dynamisch, jede Zeile exakt gleich hoch wie multi_cell-Ausgabe
        y_cursor = pdf.get_y()
        for idx, (label, value) in enumerate(rows):
            # Label-Zelle
            pdf.set_xy(x_table + img_width, y_cursor)
            x_label = pdf.get_x()
            y_label = pdf.get_y()
            # Wert-Zelle (multi_cell)
            pdf.set_xy(x_table + img_width + label_width, y_cursor)
            x_value = pdf.get_x()
            y_value = pdf.get_y()
            pdf.multi_cell(value_width, 6, value, border=1)
            y_after = pdf.get_y()
            cell_height = y_after - y_value
            # Jetzt Label-Zelle exakt so hoch wie Wert-Zelle
            pdf.set_xy(x_label, y_label)
            pdf.cell(label_width, cell_height, label, border=1)
            y_cursor += cell_height
        # Abstand nach Tabelle
        pdf.ln(8)

        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, 'Das Arbeitsmittel ist vom Arbeitnehmer ausschließlich im Rahmen seiner Tätigkeit zu benutzen. Eine Nutzung für private Zwecke ist nicht gestattet.\n\nDer Arbeitnehmer hat dafür Sorge zu tragen, dass Schäden, die am Gerät auftreten, unverzüglich dem Unternehmen gemeldet werden.\n\nSchäden, die auf normalen Verschleiß zurückzuführen sind, werden auf Kosten der Firma beseitigt. Bei Schäden, die auf unsachgemäßen Gebrauch zurückzuführen sind, behält sich der Arbeitgeber vor, diese auf Kosten des Arbeitnehmers beseitigen zu lassen.\n\nDer Arbeitnehmer ist nicht berechtigt, Arbeitsmittel Dritten zu überlassen oder Zugang zu gewähren.\n\nDer Arbeitnehmer bestätigt mit seiner Unterschrift unter diese Vereinbarung, dass er die Arbeitsmittel von der Firma in funktionsfähigem und mängelfreiem Zustand erhalten hat.\n\nEndet das Arbeitsverhältnis, hat der Arbeitnehmer die Arbeitsmittel unaufgefordert zurückzugeben. Auch während des Bestands des Arbeitsverhältnisses hat der Arbeitnehmer einer Rückgabeaufforderung durch die Firma unverzüglich Folge zu leisten.\n\nDiese Vereinbarung ist wesentlicher Bestandteil des Arbeitsvertrags. Änderungen und Ergänzungen dieser Vereinbarung bedürfen der Schriftform.')
        pdf.ln(10)
        pdf.set_font('Arial', '', 11)
        # Unterschriftenzeile
        pdf.cell(100, 10, 'Unterschrift Arbeitgeber', border=0, align='C')
        pdf.cell(100, 10, 'Unterschrift Arbeitnehmer', border=0, ln=1, align='C')
        y = pdf.get_y()
        # Getrennte Linien für Unterschriften
        # Arbeitgeber: links
        pdf.line(25, y+5, 95, y+5)
        # Arbeitnehmer: rechts
        pdf.line(125, y+5, 195, y+5)
        # Unterschrift Arbeitgeber (Bild)
        signature_employer_data = form.signature_employer.data
        if signature_employer_data and signature_employer_data.startswith('data:image'):
            header, encoded = signature_employer_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                tmp_img.write(img_bytes)
                tmp_img.flush()
                pdf.image(tmp_img.name, x=25, y=y-3, w=60)
        # Unterschrift Arbeitnehmer (Bild)
        signature_data = form.signature.data
        if signature_data and signature_data.startswith('data:image'):
            header, encoded = signature_data.split(',', 1)
            img_bytes = base64.b64decode(encoded)
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_img:
                tmp_img.write(img_bytes)
                tmp_img.flush()
                pdf.image(tmp_img.name, x=130, y=y-3, w=60)
        # Linie für Arbeitgeber direkt über Ort, Datum
        pdf.ln(13)
        pdf.set_x(20)
        pdf.cell(60, 0, '', border='T')
        pdf.ln(5)
        pdf.cell(0, 8, f'Ort, Datum: ________________________________', ln=1)

        # PDF im Uploads-Ordner speichern
        import time
        uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"asset_{asset.id}_uebergabe_{timestamp}.pdf"
        pdf_path = os.path.join(uploads_dir, pdf_filename)
        pdf.output(pdf_path)
        # Automatische Verknüpfung als Dokument
        from werkzeug.utils import secure_filename
        from mimetypes import guess_type
        # Dokument-Metadaten
        title = f"Übergabeprotokoll {asset.name} ({timestamp})"
        document_type = "other"  # oder z.B. "certificate"/"manual" bei Bedarf
        filename = pdf_filename
        file_path = pdf_path
        mime_type = guess_type(pdf_path)[0] or "application/pdf"
        size = os.path.getsize(pdf_path)
        notes = "Automatisch generiertes Übergabeprotokoll (PDF) mit digitalen Unterschriften."
        # Document-Objekt anlegen und speichern
        document = Document(
            title=title,
            document_type=document_type,
            filename=filename,
            file_path=file_path,
            mime_type=mime_type,
            size=size,
            notes=notes,
            asset_id=asset.id
        )
        db.session.add(document)
        db.session.commit()
        flash(f'PDF wurde erfolgreich erstellt und direkt als Dokument zum Asset hinzugefügt: {pdf_filename}.', 'success')
        return redirect(url_for('main.asset_details', id=asset.id))
    
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
@login_required
@admin_required
def delete_asset(id):
    """Asset und alle verknüpften Daten löschen (ohne Response/Flash)"""
    asset = Asset.query.filter_by(id=id).first_or_404()
    # Lösche alle verknüpften Dokumente
    documents = Document.query.filter_by(asset_id=id).all()
    for doc in documents:
        if doc.filename:
            try:
                os.remove(os.path.join(UPLOAD_FOLDER, doc.filename))
            except OSError:
                pass
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
    # Logging vor dem Löschen
    log = AssetLog(
        user_id=current_user.id,
        username=current_user.username,
        asset_id=asset.id,
        action='gelöscht',
        details=None,
        ip_address=request.remote_addr
    )
    db.session.add(log)
    db.session.delete(asset)
    db.session.commit()

@main.route('/assets/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_asset_route(id):
    delete_asset(id)
    flash('Asset und alle verknüpften Daten wurden erfolgreich gelöscht.', 'success')
    return jsonify({'success': True})

@main.route('/order/import_csv', methods=['GET', 'POST'])
@login_required
def import_csv_order():
    app_fields = ['Artikelnummer','Bezeichnung','Menge','Kategorie','Hersteller','Trackingnummer','Kommentar']
    preview = None
    columns = []
    mapping = None
    import_result = None
    csv_text = None
    import io, csv
    try:
        import pandas as pd
    except ImportError:
        pd = None
    if request.method == 'POST':
        if 'csvFile' in request.files:
            # Upload-Phase
            file = request.files['csvFile']
            csv_text = file.read().decode('utf-8')
            # Vorschau
            if pd:
                # Trennzeichen automatisch erkennen (Komma oder Semikolon)
                df = pd.read_csv(io.StringIO(csv_text), sep=None, engine='python')
                columns = list(df.columns)
                preview_rows = df.head(10).values.tolist()
            else:
                # Trennzeichen automatisch erkennen
                sample = csv_text[:1024]
                delimiter = ';' if ';' in sample else ','
                reader = csv.reader(io.StringIO(csv_text), delimiter=delimiter)
                rows = list(reader)
                columns = rows[0] if rows else []
                preview_rows = rows[1:11]
            preview = '<table class="table table-sm table-bordered"><thead><tr>' + ''.join(f'<th>{c}</th>' for c in columns) + '</tr></thead><tbody>'
            for row in preview_rows:
                preview += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>'
            preview += '</tbody></table>'
        elif 'csv_text' in request.form:
            # Mapping-Phase
            csv_text = request.form['csv_text']
            mapping = {field: request.form.get(f'mapping_{field}') for field in app_fields}
            # Hier: Import-Logik (Demo)
            import_result = f"Import erfolgreich! Mapping: {mapping}"
            return render_template('order/import_csv.html', preview=None, app_fields=app_fields, columns=[], mapping=mapping, csv_text=None, import_result=import_result)
    return render_template('order/import_csv.html', preview=preview, app_fields=app_fields, columns=columns, mapping=mapping, csv_text=csv_text, import_result=import_result)

@main.route('/import_assets', methods=['GET', 'POST'])
@login_required
@admin_required
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
    import qrcode
    import io
    from flask import send_file, url_for

    asset = Asset.query.filter_by(id=id).first_or_404()
    qr_url = url_for('main.asset_details', id=asset.id, _external=True)
    img = qrcode.make(qr_url)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png', as_attachment=False, download_name=f'asset_{asset.id}_qr.png')
    

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
    
    # Aktive/geplante Inventur-Session für dieses Asset suchen
    from app.models import InventorySession, InventoryItem
    active_inventory = (
        InventorySession.query
        .filter(InventorySession.status.in_(['active', 'planned']))
        .join(InventoryItem)
        .filter(InventoryItem.asset_id == asset.id)
        .order_by(InventorySession.start_date.desc())
        .first()
    )
    documents = Document.query.filter_by(asset_id=id).all()
    return render_template('asset_details.html', asset=asset, documents=documents, active_inventory=active_inventory)


@main.route('/inventory/planning', methods=['GET'])
def inventory_planning():
    """Zeigt die Inventurplanung an"""
    from .models import Location
    
    # Aktive und geplante Inventuren
    active_sessions = InventorySession.query.filter(InventorySession.status.in_(['planned', 'in_progress', 'active'])).order_by(InventorySession.start_date).all()
    
    # Abgeschlossene Inventuren
    completed_sessions = InventorySession.query.filter_by(status='completed').order_by(InventorySession.end_date.desc()).limit(5).all()
    
    locations = db.session.query(db.func.distinct(Asset.location_id)).filter(Asset.location_id != None).all()
    location_ids = [l[0] for l in locations if l[0]]
    locations = Location.query.filter(Location.id.in_(location_ids)).all() if location_ids else []
    
    return render_template('inventory/planning.html', active_sessions=active_sessions, completed_sessions=completed_sessions, locations=locations)

@main.route('/inventory/planning/new', methods=['GET', 'POST'])
@main.route('/inventory/planning/new/<int:location_id>', methods=['GET', 'POST'])
def inventory_planning_new(location_id=None):
    """Neue Inventur planen, optional mit vorselektiertem Standort"""
    from .models import Location
    
    form = InventorySessionForm()
    
    # Wenn eine Standort-ID übergeben wurde und wir im GET-Modus sind, vorausfüllen
    if location_id and request.method == 'GET':
        location = Location.query.get_or_404(location_id)
        form.location_id.data = location_id
        form.name.data = f'Inventur {location.name} {datetime.now().strftime("%d.%m.%Y")}'
        print(f"Vorselektierter Standort: {location.name} (ID: {location_id})")
    
    
    if form.validate_on_submit():
        # Konvertiere die Datumswerte zu DateTime mit Standardzeit
        start_date = datetime.combine(form.start_date.data, datetime.min.time())
        end_date = datetime.combine(form.end_date.data, datetime.max.time())
        
        session = InventorySession(
            name=form.name.data,
            start_date=start_date,
            end_date=end_date,
            location_id=form.location_id.data if form.location_id.data != 0 else None,
            notes=form.notes.data,
            status='planned'
        )
        db.session.add(session)
        db.session.commit()
        
        # Automatisch alle Assets am gewählten Standort zur Inventur hinzufügen
        assets = Asset.query.filter_by(location_id=form.location_id.data if form.location_id.data != 0 else None).all()
        for asset in assets:
            item = InventoryItem(
                session_id=session.id,
                asset_id=asset.id,
                expected_quantity=1,  # Hier explizit Soll-Menge setzen
                expected_location=session.location_obj.name if session.location_obj else asset.location
            )
            print("CREATE InventoryItem:", asset.name, "expected_quantity:", item.expected_quantity)
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
        # Prüfen, ob die Inventur bereits gestartet wurde
        if session.status == 'planned':
            flash('Die Inventur wurde noch nicht gestartet. Bitte starten Sie die Inventur, um Daten zu erfassen.', 'warning')
            return redirect(url_for('main.inventory_planning_detail', id=id))
            
        # Inline-Erfassung: Mengen und Felder für alle Gruppen übernehmen
        print("DEBUG: POST-Daten beim Speichern:", dict(request.form))
        group_count = int(request.form.get('group_count', 0))
        print(f"DEBUG: Verarbeite {group_count} Gruppen")
        updated_any = False
        for i in range(group_count):
            group_name = request.form.get(f'group_name_{i}')
            group_article_number = request.form.get(f'group_article_number_{i}')
            counted_quantity = int(request.form.get(f'counted_quantity_{i}', 0))
            damaged_quantity = int(request.form.get(f'damaged_quantity_{i}', 0))
            actual_location = request.form.get(f'actual_location_{i}', '')
            notes = request.form.get(f'notes_{i}', '')
            print(f"DEBUG: Gruppe {i}: {group_name} (Art.Nr. {group_article_number}), gezählt: {counted_quantity}, beschädigt: {damaged_quantity}")

            # Gruppensuche maximal tolerant
            def norm(val):
                return (val or '').strip().lower()
            def is_no_artnr(val):
                val_str = str(val).strip()
                return val is None or val_str == '' or val_str == '-' or val_str.lower() == 'none'
            all_items = InventoryItem.query.filter_by(session_id=session.id).all()
            key_name = norm(group_name)
            key_artnr = norm(group_article_number)
            if is_no_artnr(group_article_number):
                items_same_type = [it for it in all_items if norm(it.asset.name) == key_name and is_no_artnr(it.asset.article_number)]
            else:
                items_same_type = [it for it in all_items if norm(it.asset.name) == key_name and norm(it.asset.article_number) == key_artnr]
            print(f"DEBUG: Gruppe {i}: {len(items_same_type)} Items gefunden, die auf \"{group_name}\" passen")
            # Mengen und Felder übernehmen
            for idx, it in enumerate(items_same_type):
                if idx < counted_quantity:
                    if idx < damaged_quantity:
                        it.status = 'damaged'
                        it.condition = 'damaged'
                        print(f"DEBUG: Item ID {it.id}, Name {it.asset.name} -> beschädigt, counted_quantity=1, damaged=Ja")
                    else:
                        it.status = 'found'
                        it.condition = 'good'
                        print(f"DEBUG: Item ID {it.id}, Name {it.asset.name} -> gefunden, counted_quantity=1, damaged=Nein")
                    it.counted_quantity = 1
                else:
                    it.status = 'missing'
                    it.condition = 'missing'
                    it.counted_quantity = 0
                    print(f"DEBUG: Item ID {it.id}, Name {it.asset.name} -> fehlend, counted_quantity=0")
                it.actual_location = actual_location
                it.notes = notes
                updated_any = True
        if updated_any:
            print("DEBUG: Speichere Änderungen in Datenbank...")
            db.session.commit()
            # Direkt nach dem Commit eine Überprüfung durchführen
            verification_items = InventoryItem.query.filter_by(session_id=session.id).all()
            print("--- DEBUG Verifikation nach Speichern ---")
            for item in verification_items:
                print(f"ID: {item.id}, Asset: {item.asset.name}, Soll: {item.expected_quantity}, Ist: {item.counted_quantity}, Status: {item.status}")
            print("--- ENDE DEBUG ---")
            
            # Wenn Inventur abschließen ausgelöst wurde, leite weiter zur Abschlussroute
            if request.form.get('complete_inventory') == '1':
                # Abschluss-Logik direkt als Funktionsaufruf (POST bleibt erhalten)
                return complete_inventory(session.id)
            else:
                flash('Alle Mengen und Felder wurden gespeichert.', 'success')
                return redirect(url_for('main.inventory_planning_detail', id=session.id))

        # Ursprüngliche Standortauswahl-Logik (Assets hinzufügen)
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

    # Gruppierung nach Asset-Name und Artikelnummer (maximal tolerant)
    from collections import defaultdict
    def norm(val):
        return (val or '').strip().lower()
    def is_no_artnr(val):
        return val is None or str(val).strip() == '' or str(val).strip() == '-'
    items_grouped = defaultdict(lambda: {"name": None, "article_number": None, "category": None, "expected_location": None, "sum_expected_quantity": 0, "sum_damaged_quantity": 0, "serial_numbers": [], "statuses": set()})
    for item in items:
        name = norm(item.asset.name)
        artnr = item.asset.article_number
        key_artnr = '-' if is_no_artnr(artnr) else norm(artnr)
        key = (name, key_artnr)
        group = items_grouped[key]
        group["name"] = item.asset.name
        group["article_number"] = item.asset.article_number
        group["category"] = item.asset.category.name if item.asset.category else "-"
        group["expected_location"] = item.expected_location or "-"
        group["sum_expected_quantity"] += item.expected_quantity or 1
        # Fix: Gezählte Menge korrekt aufsummieren, nicht überschreiben
        if "sum_counted_quantity" not in group:
            group["sum_counted_quantity"] = 0
        group["sum_counted_quantity"] += item.counted_quantity or 0
        
        # Beschädigte Menge aufsummieren, wenn Status = 'damaged'
        if item.status == 'damaged':
            group["sum_damaged_quantity"] += 1
        if item.asset.serial_number:
            group["serial_numbers"].append(item.asset.serial_number)
        group["statuses"].add(item.status)
    # sets zu listen für jinja
    for group in items_grouped.values():
        group["statuses"] = list(group["statuses"])
    items_grouped = list(items_grouped.values())

    # Neue Zähllogik: Summe der Soll- und Ist-Mengen
    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    total = sum(safe_int(item.expected_quantity) for item in items)
    counted = sum(safe_int(item.counted_quantity) for item in items)
    gefunden = counted  # Die gezählte Menge ist die Anzahl der gefundenen Stücke
    # Gruppiert nach Asset-Name: Zähle, wie viele Asset-Typen noch nicht vollständig gezählt sind
    asset_groups = defaultdict(lambda: {"expected": 0, "counted": 0})
    for item in items:
        print("DEBUG item:", item.asset.name, "expected_quantity:", item.expected_quantity, "counted_quantity:", item.counted_quantity)
        key = item.asset.name
        asset_groups[key]["expected"] += safe_int(item.expected_quantity)
        asset_groups[key]["counted"] += safe_int(item.counted_quantity)
    # Debug-Ausgabe für asset_groups
    print("DEBUG asset_groups:", dict(asset_groups))
    # Ausstehende Stückzahl: Summe aller noch nicht gezählten Stücke
    ausstehende_stueckzahl = sum(
        max(int(group["expected"]) - int(group["counted"]), 0)
        for group in asset_groups.values()
        if int(group["expected"]) > 0 and int(group["counted"]) < int(group["expected"])
    )
    # Ausstehend: Anzahl Asset-Typen, bei denen noch nicht alles gezählt wurde
    ausstehende_assets = sum(
        1 for group in asset_groups.values()
        if int(group["expected"]) > 0 and int(group["counted"]) < int(group["expected"])
    )
    # Fehlend: Summe aller fehlenden Stücke
    fehlend = sum(
        max(int(group["expected"]) - int(group["counted"]), 0)
        for group in asset_groups.values()
        if int(group["expected"]) > 0
    )
    missing = fehlend
    damaged = len([item for item in items if item.status == 'damaged'])
    progress = (counted / total * 100) if total > 0 else 0

    # --- DEBUG: Ausgabe aller InventoryItems der Session ---
    print("\n--- DEBUG InventoryItems für Session", id, "---")
    for item in items:
        print(f"ID: {item.id}, Asset-ID: {item.asset_id}, Asset-Name: {getattr(item.asset, 'name', None)}, Soll: {item.expected_quantity}, Ist: {item.counted_quantity}, Status: {item.status}")
    print("--- ENDE DEBUG ---\n")
    return render_template('inventory/planning_detail.html',
                         session=session,
                         items=items,
                         items_grouped=items_grouped,
                         locations=locations,
                         total=total,
                         counted=counted,
                         gefunden=gefunden,
                         ausstehende_stueckzahl=ausstehende_stueckzahl,
                         ausstehende_assets=ausstehende_assets,
                         missing=missing,
                         damaged=damaged,
                         progress=progress)


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
    return redirect(url_for('main.inventory_planning_detail', id=id))

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
    
    # Neue Zähllogik: Summe der Soll- und Ist-Mengen
    def safe_int(val):
        try:
            return int(val)
        except (TypeError, ValueError):
            return 0

    total = sum(safe_int(item.expected_quantity) for item in items)
    counted = sum(safe_int(item.counted_quantity) for item in items)
    gefunden = counted
    ausstehende_stueckzahl = max(total - counted, 0)
    ausstehende_assets = sum(1 for item in items if safe_int(item.counted_quantity) < safe_int(item.expected_quantity))
    progress = (counted / total * 100) if total > 0 else 0

    return render_template('inventory/execute_session.html',
                         session=session,
                         items=items,
                         total=total,
                         counted=counted,
                         gefunden=gefunden,
                         ausstehende_stueckzahl=ausstehende_stueckzahl,
                         ausstehende_assets=ausstehende_assets,
                         progress=progress)


@main.route('/inventory/check_group/<int:session_id>/<group_name>/<article_number>', methods=['GET', 'POST'])
def inventory_check_group(session_id, group_name, article_number):
    session = InventorySession.query.get_or_404(session_id)
    all_items = InventoryItem.query.filter_by(session_id=session.id).all()
    def norm(val):
        return (val or '').strip().lower()
    key_name = norm(group_name)
    key_artnr = norm(article_number)
    # Maximale Toleranz: Alle Varianten von 'keine Artikelnummer' (None, '', '-') als gleich behandeln
    def is_no_artnr(val):
        return val is None or str(val).strip() == '' or str(val).strip() == '-'
    if is_no_artnr(article_number):
        items_same_type = [i for i in all_items if norm(i.asset.name) == key_name and is_no_artnr(i.asset.article_number)]
    else:
        items_same_type = [i for i in all_items if norm(i.asset.name) == key_name and norm(i.asset.article_number) == key_artnr]
    print("DEBUG [GROUP] items_same_type (ID, Status):", [(i.id, i.status) for i in items_same_type])
    if not items_same_type:
        flash('Keine passenden Assets für diese Gruppe gefunden!', 'danger')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    item = items_same_type[0]
    if request.method == 'POST':
        counted_quantity_grouped = request.form.get('counted_quantity_grouped', type=int) or 0
        damaged_quantity_grouped = request.form.get('damaged_quantity_grouped', type=int) or 0
        for idx, i in enumerate(items_same_type):
            if idx < counted_quantity_grouped:
                if idx < damaged_quantity_grouped:
                    i.status = 'damaged'
                    i.condition = 'damaged'
                else:
                    i.status = 'found'
                    i.condition = 'good'
                i.counted_quantity = 1
            else:
                i.status = 'missing'
                i.condition = 'missing'
                i.counted_quantity = 0
        db.session.commit()
        flash('Alle Mengen für diese Gruppe wurden gespeichert.', 'success')
        return redirect(url_for('main.inventory_planning_detail', id=session.id))
    # Übergabe der beiden Mengen an das Template (temporär, falls nicht im Modell)
    for i in items_same_type:
        i.counted_quantity1 = getattr(i, 'counted_quantity1', None)
        i.counted_quantity2 = getattr(i, 'counted_quantity2', None)
    return render_template('inventory/check_item.html',
                         item=item,
                         items_same_type=items_same_type,
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
        item.counted_by = getattr(current_user, "username", "anonymous")
        item.counted_at = datetime.utcnow()

        # Speichere die Zustände pro Seriennummer als JSON-Liste
        serial_statuses = []
        for serial in request.form.getlist('serial_numbers'):
            status = request.form.get(f'status_{serial}')
            if serial and status:
                serial_statuses.append({'serial_number': serial, 'status': status})
        item.serial_statuses = serial_statuses
        
        # Location korrekt?
        item.location_correct = (item.actual_location.lower() == item.expected_location.lower()) if item.actual_location and item.expected_location else False
        
        # Status basierend auf den Eingaben setzen (mindestens einer damaged/repair_needed → damaged; sonst found)
        if item.counted_quantity == 0:
            item.status = 'missing'
        elif any(s['status'] in ['damaged', 'repair_needed'] for s in serial_statuses):
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
        return redirect(url_for('main.inventory_planning_detail', id=item.session_id))
    
    # Seriennummern wie in der Planung-Ansicht aggregieren
    serial_numbers = [
        i.asset.serial_number
        for i in InventoryItem.query.filter_by(session_id=item.session_id).all()
        if i.asset and i.asset.name == item.asset.name and i.asset.serial_number
    ]

    # serial_statuses als Dict für das Template bereitstellen
    serial_statuses_dict = {}
    if item.serial_statuses:
        for entry in item.serial_statuses:
            serial_statuses_dict[entry['serial_number']] = entry['status']
    return render_template('inventory/item_detail.html', item=item, serial_numbers=serial_numbers, serial_statuses=serial_statuses_dict)


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
    
    # Prüfe pro Asset nur das Item mit der höchsten gezählten Menge
    from sqlalchemy import func, and_
    subq = db.session.query(
        InventoryItem.asset_id,
        func.max(InventoryItem.counted_quantity).label('max_counted')
    ).filter(
        InventoryItem.session_id == id
    ).group_by(InventoryItem.asset_id).subquery()

    uncounted_items = db.session.query(InventoryItem).join(
        subq,
        and_(
            InventoryItem.asset_id == subq.c.asset_id,
            InventoryItem.counted_quantity == subq.c.max_counted
        )
    ).filter(
        InventoryItem.counted_quantity == None
    ).count()
    if uncounted_items > 0:
        flash(f'Es gibt noch {uncounted_items} ungezählte Assets in dieser Inventur.', 'warning')
        return redirect(url_for('main.inventory_planning_detail', id=id))
    
    # Setze Status für alle Items
    for item in session.items:
        if item.counted_quantity is not None:
            # Prüfe auf beschädigte Seriennummern
            has_damaged_serial = False
            if item.serial_statuses:
                has_damaged_serial = any(s.get('status') in ['damaged', 'repair_needed'] for s in item.serial_statuses)
                
            # Prüfe Zustand - verschiedene Prüfungen für "damaged"
            if (item.condition is not None and (item.condition == 'damaged' or item.condition == 'repair_needed')) or \
               item.status == 'damaged' or has_damaged_serial:
                item.status = 'damaged'
                # Debug-Info ausgeben
                print(f"DEBUG: Item {item.id} (Asset: {item.asset.name if item.asset else 'N/A'}) als DAMAGED markiert. Grund: condition={item.condition}, has_damaged_serial={has_damaged_serial}")
            else:
                item.status = 'found'
                print(f"DEBUG: Item {item.id} (Asset: {item.asset.name if item.asset else 'N/A'}) als FOUND markiert.")
        else:
            item.status = 'missing'
            print(f"DEBUG: Item {item.id} (Asset: {item.asset.name if item.asset else 'N/A'}) als MISSING markiert.")


        # Standortprüfung
        if item.actual_location and item.expected_location:
            item.location_correct = (item.actual_location == item.expected_location)

    # Setze Status auf completed
    session.status = 'completed'
    session.end_date = datetime.utcnow()
    db.session.commit()
    
    flash('Inventur wurde erfolgreich abgeschlossen!', 'success')
    return redirect(url_for('main.inventory_reports'))

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
            qty_field = f"expected_quantity_{asset_id}"
            try:
                expected_quantity = int(request.form.get(qty_field, 1))
            except ValueError:
                expected_quantity = 1
            # Prüfen wie viele Items es schon gibt
            existing_items = InventoryItem.query.filter_by(session_id=id, asset_id=asset_id).count()
            # Lege so viele neue Items an, dass insgesamt expected_quantity erreicht wird
            for _ in range(existing_items, expected_quantity):
                item = InventoryItem(
                    session_id=id,
                    asset_id=asset_id,
                    status='pending',
                    expected_quantity=1
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

from sqlalchemy.orm import joinedload

@main.route('/inventory/reports')

def inventory_reports():
    """Zeigt eine Übersicht aller abgeschlossenen Inventuren mit Berichten"""
    completed_sessions = (
        InventorySession.query
        .options(joinedload(InventorySession.items))
        .filter_by(status='completed')
        .order_by(InventorySession.end_date.desc())
        .all()
    )
    # Zusammenfassung nach Typ-Summen-Logik
    session_summaries = {}
    for session in completed_sessions:
        # Aggregiere pro Typ (Name + Artikelnummer)
        type_groups = {}
        damaged = 0
        for item in session.items:
            key = (item.asset.name, item.asset.article_number or "-")
            if key not in type_groups:
                type_groups[key] = {"expected": 0, "counted": 0, "damaged": 0}
            type_groups[key]["expected"] += item.expected_quantity or 0
            type_groups[key]["counted"] += item.counted_quantity or 0
            if item.status == 'damaged':
                type_groups[key]["damaged"] += 1
                damaged += 1
        found = 0
        missing = 0
        total = 0
        for stats in type_groups.values():
            expected_sum = stats["expected"]
            counted_sum = stats["counted"]
            total += expected_sum  # Nur die Typ-Summe zählt!
            if counted_sum >= expected_sum and expected_sum > 0:
                found += expected_sum
            else:
                found += counted_sum if counted_sum > 0 else 0
                missing += expected_sum - counted_sum if expected_sum > counted_sum else 0
        session_summaries[session.id] = {
            'found': found,
            'missing': missing,
            'damaged': damaged,
            'total': total  # Nur die Typ-Summe, nicht die Einzel-Items!
        }

    return render_template('inventory/reports.html', completed_sessions=completed_sessions, session_summaries=session_summaries)


@main.route('/inventory/reports/<int:id>')

def inventory_report_detail(id):
    """Zeigt detaillierte Informationen zu einer abgeschlossenen Inventur"""
    session = InventorySession.query.get_or_404(id)
    if session.status != 'completed':
        flash('Diese Inventur ist noch nicht abgeschlossen.', 'warning')
        return redirect(url_for('main.inventory_reports'))
    
    # Importe zusammenfassen
    from collections import defaultdict
    import datetime
    from collections import Counter
    
    # Debug-Informationen sammeln
    print('--- DEBUG für Bericht ---')
    for item in session.items:
        print(f'ID: {item.id}, Asset: {item.asset.name}, Status: {item.status}, counted_quantity: {item.counted_quantity}')
    
    # Zählung übereinstimmend mit der Übersichtsseite: Typ-basierte Aggregationsmethode
    # Aggregiere pro Typ (Name + Artikelnummer)
    type_groups = {}
    damaged = 0
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        if key not in type_groups:
            type_groups[key] = {"expected": 0, "counted": 0, "damaged": 0}
        type_groups[key]["expected"] += item.expected_quantity or 0
        type_groups[key]["counted"] += item.counted_quantity or 0
        if item.status == 'damaged':
            type_groups[key]["damaged"] += 1
            damaged += 1
    
    # Nach Typ-Summen-Logik wie in inventory_reports
    found = 0
    missing = 0
    total = 0
    for stats in type_groups.values():
        expected_sum = stats["expected"]
        counted_sum = stats["counted"]
        total += expected_sum  # Nur die Typ-Summe zählt!
        if counted_sum >= expected_sum and expected_sum > 0:
            found += expected_sum
        else:
            found += counted_sum if counted_sum > 0 else 0
            missing += expected_sum - counted_sum if expected_sum > counted_sum else 0
    
    summary = {'found': found, 'missing': missing, 'damaged': damaged, 'total': total}
    
    print(f"Status-Zählung direkt: found={found}, missing={missing}, damaged={damaged}, total={total}")
    
    # Stelle sicher, dass diese Summen direkt an das Template übergeben werden
    # und nicht durch die nachfolgenden Berechnungen überschrieben werden
    print(f"Finale Summary: found={summary['found']}, missing={summary['missing']}, damaged={summary['damaged']}, total={summary['total']}")
    print('--- ENDE DEBUG Bericht ---')
    
    # Gruppiere nach Gerätetyp (Name + Artikelnummer) und berechne Typ-Status
    # NUR EINMAL definieren (doppelter Code entfernt)
    type_stats = {}
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        if key not in type_stats:
            type_stats[key] = {"expected": 0, "counted": 0, "damaged": False, "missing": False, "found": False}
        
        type_stats[key]["expected"] += item.expected_quantity or 0
        type_stats[key]["counted"] += item.counted_quantity if item.counted_quantity is not None else 0
        
        # Übertrage den Status des Items auf den Typ
        if item.status == 'damaged':
            type_stats[key]["damaged"] = True
        elif item.status == 'found':
            type_stats[key]["found"] = True
        elif item.status == 'missing':
            type_stats[key]["missing"] = True
    
    # Bestimme den kombinierten Status pro Typ - Priorität: beschädigt > fehlend > gefunden
    type_status = {}
    for key, stats in type_stats.items():
        if stats["damaged"]:
            type_status[key] = 'damaged'
        elif stats["missing"]:
            type_status[key] = 'missing'
        elif stats["found"] or (stats["counted"] >= stats["expected"] and stats["expected"] > 0):
            type_status[key] = 'found'
        else:
            type_status[key] = 'missing'
    # Erzeuge Asset-Liste mit dynamisch berechnetem Status - JSON-serialisierbar
    asset_list = []
    for item in session.items:
        key = (item.asset.name, item.asset.article_number or "-")
        dyn_status = type_status[key]
        stats = type_stats[key]
        
        # Serialisiere das Asset und andere komplexe Objekte
        asset_data = {
            "id": item.asset.id,
            "name": item.asset.name,
            "serial_number": item.asset.serial_number,
            "article_number": item.asset.article_number,
            "location": {
                "id": item.asset.location.id if item.asset.location else None,
                "name": item.asset.location.name if item.asset.location else None
            } if item.asset.location else None
        }
        
        # Erstelle ein serialisierbares Dictionary für das Inventur-Item
        item_data = {
            "id": item.id,
            "status": item.status,
            "counted_quantity": item.counted_quantity,
            "expected_quantity": item.expected_quantity,
            "counted_at": item.counted_at.isoformat() if item.counted_at else None,
            "actual_location": item.actual_location,
            "condition": item.condition,
            "asset": asset_data
        }
        
        # Füge das serialisierbare Item zur Liste hinzu
        asset_list.append({
            "item": item_data,
            "dyn_status": dyn_status,
            "expected": stats["expected"],
            "counted": stats["counted"],
            "diff": stats["counted"] - stats["expected"]
        })
    # Aggregierte Liste pro Asset-Typ für die Übersichtstabelle
    asset_type_list = []
    for key, stats in type_stats.items():
        name, article_number = key
        dyn_status = type_status[key]
        asset_type_list.append({
            "name": name,
            "article_number": article_number,
            "dyn_status": dyn_status,
            "expected": stats["expected"],
            "counted": stats["counted"],
            "diff": stats["counted"] - stats["expected"]
        })
        # Zeitverlauf: Zählungen pro Tag
    from collections import Counter
    import datetime
    timeline_counter = Counter()
    for item in session.items:
        if item.counted_at:
            day = item.counted_at.strftime('%Y-%m-%d')
            timeline_counter[day] += 1
    timeline_labels = sorted(timeline_counter.keys())
    timeline_data = [timeline_counter[day] for day in timeline_labels]

    # Kategorien-Übersicht: Anzahl pro Kategorie
    category_counter = Counter()
    for item in session.items:
        cat = getattr(item.asset, 'category', 'Unbekannt') or 'Unbekannt'
        # Falls cat ein Objekt ist, nutze den Namen
        if hasattr(cat, 'name'):
            cat_label = cat.name
        else:
            cat_label = str(cat)
        category_counter[cat_label] += 1
    category_labels = list(category_counter.keys())
    category_counts = [category_counter[cat] for cat in category_labels]

    # Standort-Analyse: Anzahl Assets pro Standort
    from .models import Location
    
    # Vorbereiten der Zählung pro Standort
    location_counter = Counter()
    
    # Direktes Abfragen der Assets pro Standort mit Namen
    for item in session.items:
        # Standardwert falls kein Asset existiert
        if not item.asset:
            location_label = 'Unbekannt'
            location_counter[location_label] += 1
            continue
            
        # Asset existiert, hole den Standortnamen
        location_id = getattr(item.asset, 'location_id', None)
        
        if not location_id:
            location_label = 'Kein Standort'
        else:
            # Location direkt abfragen
            location = Location.query.get(location_id)
            location_label = location.name if location else f'Standort {location_id}'
            
        location_counter[location_label] += 1
    
    # Sortiere die Standorte für bessere Lesbarkeit
    location_labels = sorted(location_counter.keys())
    location_counts = [location_counter[loc] for loc in location_labels]
    
    # Debug-Ausgabe
    print("Debug Location Labels:", location_labels)
    print("Debug Location Counts:", location_counts)

    # WICHTIG: Explizit die korrekten Werte direkt definieren
    # Diese werden im Template unter "Gefunden: X von Y" verwendet
    gefunden = found
    fehlend = missing
    beschaedigt = damaged
    gesamt = total
    
    return render_template(
        'inventory/report_detail.html', 
        session=session, 
        summary=summary, 
        gefunden=gefunden,
        fehlend=fehlend,
        beschaedigt=beschaedigt,
        gesamt=gesamt,
        asset_list=sorted(asset_list, key=lambda x: x['item']['asset']['name']), 
        asset_type_list=asset_type_list,
        timeline_labels=timeline_labels,
        timeline_data=timeline_data,
        category_labels=category_labels,
        category_counts=category_counts,
        location_labels=location_labels,
        location_counts=location_counts
    )



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
    # Zeigt die Historie aller Inventuren
    sessions = InventorySession.query.filter_by(status='completed').order_by(InventorySession.end_date.desc()).all()
    return render_template('inventory/history.html', sessions=sessions)

@main.route('/inventory/location/<int:location_id>/plan', methods=['GET', 'POST'])
def inventory_location_plan(location_id):
    """Inventurplanung für einen bestimmten Standort"""
    from .models import Location
    from .forms import InventorySessionForm
    
    location = Location.query.get_or_404(location_id)
    
    # Formular mit vorausgefülltem Standort initialisieren
    form = InventorySessionForm()
    form.location_id.data = location_id
    form.name.data = f'Inventur {location.name} {datetime.now().strftime("%d.%m.%Y")}'
    
    # Bestehende Inventuren für diesen Standort anzeigen
    existing_sessions = InventorySession.query.filter_by(location_id=location_id).order_by(InventorySession.start_date.desc()).all()
    
    if form.validate_on_submit():
        # Neue Inventur für diesen Standort erstellen
        session = InventorySession(
            name=form.name.data,
            location_id=location_id,
            status='planned',
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            notes=form.notes.data
        )
        db.session.add(session)
        db.session.commit()
        
        # Alle Assets an diesem Standort zur Inventur hinzufügen
        for asset in location.assets:
            item = InventoryItem(
                session_id=session.id,
                asset_id=asset.id,
                status='pending',
                expected_quantity=1,
                expected_location=location.name
            )
            db.session.add(item)
        
        db.session.commit()
        
        # Standort-Inventurstatus aktualisieren
        location.inventory_status = 'Inventur geplant'
        location.last_inventory_date = datetime.now()
        db.session.commit()
        
        flash(f'Inventur für {location.name} wurde geplant.', 'success')
        return redirect(url_for('main.location_detail', id=location_id))
    
    return render_template('inventory/planning_location.html', form=form, location=location, existing_sessions=existing_sessions)

@main.route('/inventory/location/<int:location_id>/history')
def inventory_location_history(location_id):
    """Zeigt die Inventurhistorie für einen bestimmten Standort"""
    from .models import Location
    
    location = Location.query.get_or_404(location_id)
    sessions = InventorySession.query.filter_by(
        location_id=location_id, 
        status='completed'
    ).order_by(InventorySession.end_date.desc()).all()
    
    return render_template('inventory/location_history.html', location=location, sessions=sessions)
