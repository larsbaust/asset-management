from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, TextAreaField, FloatField, DateTimeField, BooleanField, SubmitField, FileField, IntegerField
from wtforms.fields import DateField
from wtforms.validators import DataRequired, Length, Optional, NumberRange
from flask_wtf.file import FileAllowed
from datetime import datetime

# Vordefinierte Listen
LOCATIONS = [
    ('', 'Standort auswählen...'),
    ('Aachen', 'Aachen'),
    ('Berlin Alexa', 'Berlin Alexa'),
    ('Berlin Alexanderplatz', 'Berlin Alexanderplatz'),
    ('Berlin Brunnenstr.', 'Berlin Brunnenstr.'),
    ('Berlin Designer Outlet', 'Berlin Designer Outlet'),
    ('Berlin Friedrichstr.', 'Berlin Friedrichstr.'),
    ('Mall of Berlin', 'Mall of Berlin'),
    ('Berlin Tauentzienstraße', 'Berlin Tauentzienstraße'),
    ('Bonn', 'Bonn'),
    ('Braunschweig', 'Braunschweig'),
    ('Dortmund', 'Dortmund'),
    ('Dresden', 'Dresden'),
    ('Düsseldorf-Altstadt', 'Düsseldorf-Altstadt'),
    ('Düsseldorf-Bilk', 'Düsseldorf-Bilk'),
    ('Düsseldorf Hbf', 'Düsseldorf Hbf'),
    ('Düsseldorf Schadowstr.', 'Düsseldorf Schadowstr.'),
    ('Essen Hbf', 'Essen Hbf'),
    ('Essen Kettwiger Str.', 'Essen Kettwiger Str.'),
    ('Flensburg', 'Flensburg'),
    ('Frankfurt Hbf', 'Frankfurt Hbf'),
    ('Frankfurt Kaiserstr.', 'Frankfurt Kaiserstr.'),
    ('Hamburg Hbf', 'Hamburg Hbf'),
    ('Hamburg Bergstr.', 'Hamburg Bergstr.'),
    ('Hannover Hbf', 'Hannover Hbf'),
    ('Hannover Karmarschstr.', 'Hannover Karmarschstr.'),
    ('Heidelberg', 'Heidelberg'),
    ('Karlsruhe', 'Karlsruhe'),
    ('Koblenz', 'Koblenz'),
    ('Köln Ehrenstr.', 'Köln Ehrenstr.'),
    ('Köln Hbf', 'Köln Hbf'),
    ('Leipzig Hbf', 'Leipzig Hbf'),
    ('Mainz Hbf', 'Mainz Hbf'),
    ('Mannheim', 'Mannheim'),
    ('Metzingen Outletcity', 'Metzingen Outletcity'),
    ('Münster Hbf', 'Münster Hbf'),
    ('Münster Salzstr.', 'Münster Salzstr.'),
    ('Neumünster Designer Outlet', 'Neumünster Designer Outlet'),
    ('Nürnberg', 'Nürnberg'),
    ('Oberhausen CentrO', 'Oberhausen CentrO'),
    ('Ochtrup Designer Outlet', 'Ochtrup Designer Outlet'),
    ('Stuttgart Bolzstr.', 'Stuttgart Bolzstr.'),
    ('Stuttgart Milaneo', 'Stuttgart Milaneo'),
    ('Wolfsburg Designer Outlet', 'Wolfsburg Designer Outlet'),
    ('Zweibrücken Fashion Outlet', 'Zweibrücken Fashion Outlet')
]

# Initiale Kategorien
CATEGORIES = [
    ('', 'Kategorie auswählen...'),
    ('Hardware', 'Hardware'),
    ('Software', 'Software'),
    ('Möbel', 'Möbel'),
    ('Büro', 'Büro'),
    ('Netzwerk', 'Netzwerk'),
    ('Sicherheit', 'Sicherheit'),
    ('Audio', 'Audio'),
    ('Video', 'Video'),
    ('Sonstiges', 'Sonstiges')
]

class AssetForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Beschreibung', validators=[Optional()])
    image = FileField('Bild', validators=[Optional(), FileAllowed(['jpg', 'png', 'jpeg', 'gif'], 'Nur Bilder erlaubt!')])
    article_number = StringField('Artikelnummer', validators=[Optional(), Length(max=100)])
    ean = StringField('EAN', validators=[Optional(), Length(max=13)])
    value = FloatField('Wert (€)', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('active', 'Aktiv'),
        ('inactive', 'Inaktiv'),
        ('on_loan', 'Ausgeliehen')
    ], validators=[DataRequired()])
    category = SelectField('Kategorie', choices=CATEGORIES, validators=[DataRequired()])
    assignments = SelectField('Zuordnungen', choices=[], validators=[Optional()], render_kw={'multiple': True})
    manufacturers = SelectField('Hersteller', choices=[], validators=[Optional()], render_kw={'multiple': True})
    suppliers = SelectField('Lieferanten', choices=[], validators=[Optional()], render_kw={'multiple': True})
    location = SelectField('Standort', choices=LOCATIONS, validators=[Optional()])
    serial_number = StringField('Seriennummer', validators=[Optional(), Length(max=255)])
    purchase_date = DateField('Anschaffungsdatum', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Speichern')

    def __init__(self, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        # Die Choices für die SelectFields werden dynamisch aus der Datenbank geladen
        from .models import Assignment, Manufacturer, Supplier
        self.assignments.choices = [(a.id, a.name) for a in Assignment.query.order_by(Assignment.name).all()]
        self.manufacturers.choices = [(m.id, m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()]
        self.suppliers.choices = [(s.id, s.name) for s in Supplier.query.order_by(Supplier.name).all()]

class LoanForm(FlaskForm):
    """Formular für das Ausleihen von Assets"""
    borrower_name = StringField('Name des Ausleihenden', validators=[DataRequired()])
    start_date = DateTimeField('Ausleihdatum', validators=[DataRequired()], default=datetime.utcnow)
    expected_return_date = DateTimeField('Erwartetes Rückgabedatum', validators=[DataRequired()])
    notes = TextAreaField('Notizen', validators=[Optional()])
    submit = SubmitField('Ausleihen')

    def validate_expected_return_date(self, field):
        """Validiere, dass das Rückgabedatum nach dem Ausleihdatum liegt"""
        if field.data <= self.start_date.data:
            raise ValidationError('Das Rückgabedatum muss nach dem Ausleihdatum liegen.')

class DocumentForm(FlaskForm):
    title = StringField('Titel', validators=[DataRequired(), Length(max=100)])
    document_type = SelectField('Dokumenttyp', choices=[
        ('manual', 'Handbuch'),
        ('invoice', 'Rechnung'),
        ('warranty', 'Garantie'),
        ('certificate', 'Zertifikat'),
        ('other', 'Sonstiges')
    ], validators=[DataRequired()])
    file = FileField('Datei', validators=[
        DataRequired(),
        FileAllowed(['pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png'], 'Nur PDF, Word und Bilder erlaubt!')
    ])
    notes = TextAreaField('Notizen')
    submit = SubmitField('Dokument hochladen')

class CostEntryForm(FlaskForm):
    """Formular für Kosteneintrag"""
    cost_type = SelectField('Kostenart', choices=[
        ('purchase', 'Anschaffung'),
        ('maintenance', 'Wartung'),
        ('repair', 'Reparatur'),
        ('upgrade', 'Upgrade/Erweiterung'),
        ('insurance', 'Versicherung'),
        ('other', 'Sonstiges')
    ], validators=[DataRequired()])
    date = DateTimeField('Datum', validators=[DataRequired()], default=datetime.utcnow)
    amount = FloatField('Betrag (€)', validators=[DataRequired(), NumberRange(min=0)])
    description = TextAreaField('Beschreibung')
    receipt = FileField('Beleg', validators=[
        Optional(),
        FileAllowed(['pdf', 'jpg', 'jpeg', 'png'], 'Nur PDF und Bilder erlaubt!')
    ])
    submit = SubmitField('Kosteneintrag hinzufügen')

class InventorySessionForm(FlaskForm):
    """Formular für die Planung einer neuen Inventur"""
    name = StringField('Name der Inventur', validators=[DataRequired(), Length(max=100)])
    start_date = DateField('Startdatum', validators=[DataRequired()], format='%Y-%m-%d')
    end_date = DateField('Enddatum', validators=[DataRequired()], format='%Y-%m-%d')
    location = SelectField('Standort', choices=LOCATIONS, validators=[DataRequired()])
    notes = TextAreaField('Notizen', validators=[Optional()])
    submit = SubmitField('Inventur planen')

    def validate_end_date(self, field):
        """Stellt sicher, dass das Enddatum nach dem Startdatum liegt"""
        if field.data <= self.start_date.data:
            raise ValidationError('Das Enddatum muss nach dem Startdatum liegen.')

class InventoryTeamForm(FlaskForm):
    """Formular für die Erstellung eines Inventur-Teams"""
    name = StringField('Team Name', validators=[DataRequired(), Length(max=100)])
    leader_name = StringField('Team Leiter', validators=[DataRequired(), Length(max=100)])
    members = TextAreaField('Team Mitglieder (durch Komma getrennt)', validators=[Optional()])
    area = StringField('Zugewiesener Bereich', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Team erstellen')

class InventoryCheckForm(FlaskForm):
    """Formular für die Erfassung eines Assets während der Inventur"""
    status = SelectField('Status', choices=[
        ('found', 'Gefunden'),
        ('missing', 'Nicht gefunden'),
        ('damaged', 'Beschädigt')
    ], validators=[DataRequired()])
    
    counted_quantity = IntegerField('Gezählte Menge', validators=[Optional()], default=1)
    
    location_correct = SelectField('Standort korrekt?', choices=[
        ('yes', 'Ja'),
        ('no', 'Nein')
    ], validators=[DataRequired()])
    
    actual_location = StringField('Tatsächlicher Standort', validators=[Optional(), Length(max=100)])
    
    condition = SelectField('Zustand', choices=[
        ('good', 'Gut'),
        ('damaged', 'Beschädigt'),
        ('repair_needed', 'Reparaturbedürftig')
    ], validators=[Optional()])
    
    condition_notes = TextAreaField('Zustandsbeschreibung', validators=[Optional(), Length(max=1000)])
    
    notes = TextAreaField('Notizen', validators=[Optional(), Length(max=1000)])
    
    image = FileField('Foto (optional)', validators=[
        Optional(),
        FileAllowed(['jpg', 'png'], 'Nur Bilder erlaubt!')
    ])
    
    submit = SubmitField('Speichern')
