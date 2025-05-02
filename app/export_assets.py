import csv
from flask import Blueprint, render_template, request, Response
from app.models import Asset

export_assets = Blueprint('export_assets', __name__)

# Diese Felder stehen im System zur Verfügung
SYSTEM_FIELDS = [
    'name', 'article_number', 'serial_number', 'category', 'value', 'manufacturers', 'assignments'
]
FIELD_LABELS = {
    'name': 'Name',
    'article_number': 'Artikelnummer',
    'serial_number': 'Seriennummer',
    'category': 'Kategorie',
    'value': 'Wert',
    'manufacturers': 'Hersteller',
    'assignments': 'Zuordnung',
}

@export_assets.route('/export/assets', methods=['GET', 'POST'])
def export_assets_select():
    if request.method == 'POST':
        selected_fields = request.form.getlist('fields')
        custom_names = [request.form.get(f'colname_{f}', f) for f in selected_fields]
        # CSV erzeugen
        def generate():
            yield ';'.join(custom_names) + '\n'
            for asset in Asset.query.all():
                row = []
                for f in selected_fields:
                    val = getattr(asset, f, '')
                    if f == 'category' and asset.category:
                        val = asset.category.name
                    elif f == 'manufacturers' and asset.manufacturers:
                        val = ', '.join([m.name for m in asset.manufacturers])
                    elif f == 'assignments' and asset.assignments:
                        val = ', '.join([a.name for a in asset.assignments])
                    row.append(str(val) if val is not None else '')
                yield ';'.join(row) + '\n'
        return Response(generate(), mimetype='text/csv', headers={
            'Content-Disposition': 'attachment; filename=assets_export.csv'
        })
    return render_template('export_assets.html', system_fields=SYSTEM_FIELDS, field_labels=FIELD_LABELS)
