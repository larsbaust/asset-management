from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo
from wtforms import StringField, SelectField, SelectMultipleField, TextAreaField, FloatField, DateTimeField, BooleanField, SubmitField, FileField, IntegerField
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
    category = SelectField('Kategorie', choices=[], validators=[DataRequired()])
    assignments = SelectMultipleField('Zuordnungen', choices=[], validators=[Optional()])
    manufacturers = SelectMultipleField('Hersteller', choices=[], validators=[Optional()])
    suppliers = SelectMultipleField('Lieferanten', choices=[], validators=[Optional()])
    location_id = SelectField('Standort', coerce=int, choices=[], validators=[Optional()])
    serial_number = StringField('Seriennummer', validators=[Optional(), Length(max=255)])
    purchase_date = DateField('Anschaffungsdatum', validators=[Optional()], format='%Y-%m-%d')
    submit = SubmitField('Speichern')

    def __init__(self, *args, **kwargs):
        super(AssetForm, self).__init__(*args, **kwargs)
        self.update_choices()
    
    def update_choices(self):
        """Aktualisiert die Dropdown-Choices mit aktuellen Daten aus der Datenbank"""
        from .models import Assignment, Manufacturer, Supplier, Category, Location
        self.assignments.choices = [(str(a.id), a.name) for a in Assignment.query.order_by(Assignment.name).all()]
        self.manufacturers.choices = [(str(m.id), m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()]
        self.suppliers.choices = [(str(s.id), s.name) for s in Supplier.query.order_by(Supplier.name).all()]
        self.category.choices = [(str(c.id), c.name) for c in Category.query.order_by(Category.name).all()]
        self.location_id.choices = [(0, 'Standort wählen...')] + [(l.id, l.name) for l in Location.query.order_by(Location.name).all()]

class LocationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    street = StringField('Straße', validators=[Optional(), Length(max=255)])
    postal_code = StringField('PLZ', validators=[Optional(), Length(max=20)])
    city = StringField('Stadt', validators=[Optional(), Length(max=100)])
    state = StringField('Bundesland', validators=[Optional(), Length(max=100)])
    size_sqm = FloatField('Größe (m²)', validators=[Optional()])
    seats = IntegerField('Sitzplätze', validators=[Optional()])
    description = TextAreaField('Beschreibung', validators=[Optional()])
    image = FileField('Standort-Bild', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Nur Bilder erlaubt!')])
    latitude = FloatField('Breitengrad', validators=[Optional()])
    longitude = FloatField('Längengrad', validators=[Optional()])
    # Google Reviews & Navigation Fields
    google_rating = FloatField('Google Bewertung (1.0-5.0)', validators=[Optional(), NumberRange(min=1.0, max=5.0)])
    google_reviews_count = IntegerField('Anzahl Google Bewertungen', validators=[Optional(), NumberRange(min=0)])
    google_maps_url = StringField('Google Maps URL', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Speichern')

class LoanForm(FlaskForm):
    """Formular für das Ausleihen von Assets"""
    borrower_name = StringField('Name des Ausleihenden', validators=[DataRequired()])
    start_date = DateField('Ausleihdatum', validators=[DataRequired()], format='%Y-%m-%d')
    expected_return_date = DateTimeField('Erwartetes Rückgabedatum', validators=[Optional()])
    notes = TextAreaField('Notizen', validators=[Optional()])
    signature = StringField('Unterschrift (Base64)', validators=[Optional()])
    signature_employer = StringField('Unterschrift Arbeitgeber (Base64)', validators=[Optional()])
    submit = SubmitField('Ausleihen')

    def validate_expected_return_date(self, field):
        """Validiere, dass das Rückgabedatum nach dem Ausleihdatum liegt"""
        if field.data <= self.start_date.data:
            raise ValidationError('Das Rückgabedatum muss nach dem Ausleihdatum liegen.')

class MultiLoanForm(FlaskForm):
    """Formular für eine Sammelausleihe mehrerer Assets"""
    borrower_name = StringField('Name des Ausleihenden', validators=[DataRequired()])
    start_date = DateField('Ausleihdatum', validators=[DataRequired()], format='%Y-%m-%d')
    expected_return_date = DateTimeField('Erwartetes Rückgabedatum', validators=[Optional()])
    notes = TextAreaField('Notizen', validators=[Optional()])
    signature = StringField('Unterschrift (Base64)', validators=[Optional()])
    signature_employer = StringField('Unterschrift Arbeitgeber (Base64)', validators=[Optional()])
    submit = SubmitField('Sammelausleihe speichern')

    def validate_expected_return_date(self, field):
        if field.data and self.start_date.data and field.data <= self.start_date.data:
            raise ValidationError('Das Rückgabedatum muss nach dem Ausleihdatum liegen.')

class LocationImageForm(FlaskForm):
    file = FileField('Datei (Bild oder PDF)', validators=[DataRequired(), FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'pdf'], 'Nur Bilder oder PDFs erlaubt!')])
    description = StringField('Beschreibung', validators=[Optional(), Length(max=255)])
    comment = TextAreaField('Kommentar', validators=[Optional()])
    submit = SubmitField('Hochladen')

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
    location_id = SelectField('Standort', coerce=int, choices=[], validators=[DataRequired()])
    notes = TextAreaField('Notizen', validators=[Optional()])
    submit = SubmitField('Inventur planen')

    def __init__(self, *args, **kwargs):
        super(InventorySessionForm, self).__init__(*args, **kwargs)
        from .models import Location
        self.location_id.choices = [(0, 'Standort auswählen...')] + [(l.id, l.name) for l in Location.query.order_by(Location.name).all()]

    # Stellt sicher, dass das Enddatum nach dem Startdatum liegt
    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError('Das Enddatum muss nach dem Startdatum liegen.')

class InventoryTeamForm(FlaskForm):
    """Formular für die Erstellung eines Inventur-Teams"""
    name = StringField('Team Name', validators=[DataRequired(), Length(max=100)])
    leader_name = StringField('Team Leiter', validators=[DataRequired(), Length(max=100)])
    members = TextAreaField('Team Mitglieder (durch Komma getrennt)', validators=[Optional()])
    area = StringField('Zugewiesener Bereich', validators=[Optional(), Length(max=100)])
    submit = SubmitField('Team erstellen')



class LoginForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Passwort', validators=[DataRequired()])
    remember_me = BooleanField('Angemeldet bleiben')
    submit = SubmitField('Login')

class RegisterForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Passwort', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Passwort bestätigen', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Rolle', coerce=int, validators=[DataRequired()])
    vorname = StringField('Vorname', validators=[DataRequired(), Length(max=80)])
    nachname = StringField('Nachname', validators=[DataRequired(), Length(max=80)])
    email = StringField('E-Mail', validators=[DataRequired(), Length(max=120)])
    profile_image = FileField('Profilbild', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Nur Bilder erlaubt!')])
    street = StringField('Straße', validators=[Optional(), Length(max=120)])
    postal_code = StringField('PLZ', validators=[Optional(), Length(max=20)])
    city = StringField('Stadt', validators=[Optional(), Length(max=80)])
    phone = StringField('Telefon', validators=[Optional(), Length(max=40)])
    submit = SubmitField('Registrieren')

    def __init__(self, *args, **kwargs):
        super(RegisterForm, self).__init__(*args, **kwargs)
        from .models import Role
        self.role.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]

class EditUserForm(FlaskForm):
    username = StringField('Benutzername', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Neues Passwort', validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField('Passwort bestätigen', validators=[Optional(), EqualTo('password', message='Passwörter stimmen nicht überein')])
    role = SelectField('Rolle', coerce=int, validators=[DataRequired()])
    vorname = StringField('Vorname', validators=[DataRequired(), Length(max=80)])
    nachname = StringField('Nachname', validators=[DataRequired(), Length(max=80)])
    email = StringField('E-Mail', validators=[DataRequired(), Length(max=120)])
    profile_image = FileField('Profilbild', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Nur Bilder erlaubt!')])
    street = StringField('Straße', validators=[Optional(), Length(max=120)])
    postal_code = StringField('PLZ', validators=[Optional(), Length(max=20)])
    city = StringField('Stadt', validators=[Optional(), Length(max=80)])
    phone = StringField('Telefon', validators=[Optional(), Length(max=40)])
    submit = SubmitField('Speichern')

    def __init__(self, *args, **kwargs):
        super(EditUserForm, self).__init__(*args, **kwargs)
        from .models import Role
        self.role.choices = [(r.id, r.name) for r in Role.query.order_by(Role.name).all()]
class ResetPasswordForm(FlaskForm):
    email = StringField('E-Mail-Adresse', validators=[DataRequired(), Length(max=120)])
    submit = SubmitField('Link zum Zurücksetzen senden')

# --- ENDE AUTH FORMS ---

class ProfileForm(FlaskForm):
    vorname = StringField('Vorname', validators=[DataRequired(), Length(max=80)])
    nachname = StringField('Nachname', validators=[DataRequired(), Length(max=80)])
    email = StringField('E-Mail', validators=[DataRequired(), Length(max=120)])
    # profile_image entfernt, da Upload über Modal läuft
    street = StringField('Straße', validators=[Optional(), Length(max=120)])
    postal_code = StringField('PLZ', validators=[Optional(), Length(max=20)])
    city = StringField('Stadt', validators=[Optional(), Length(max=80)])
    phone = StringField('Telefon', validators=[Optional(), Length(max=40)])
    submit = SubmitField('Profil speichern')


from wtforms import widgets, SelectMultipleField

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class RoleForm(FlaskForm):
    name = StringField('Rollenname', validators=[DataRequired(), Length(max=50)])
    description = StringField('Beschreibung', validators=[Optional(), Length(max=255)])
    permissions = MultiCheckboxField('Rechte', coerce=int)
    permission_descriptions = {}
    category_order = ['Assets', 'Dashboard', 'Administration', 'Import', 'Backup', 'Sonstiges']

    submit = SubmitField('Speichern')

    def __init__(self, *args, **kwargs):
        super(RoleForm, self).__init__(*args, **kwargs)
        from .models import Permission
        perms = Permission.query.order_by(Permission.name).all()
        self.permissions.choices = [(p.id, p.name) for p in perms]

        # Mapping: permission.id -> description / category
        self.permission_descriptions = {p.id: (p.description or p.name) for p in perms}

        permission_category_map = {
            'view_assets': 'Assets',
            'edit_assets': 'Assets',
            'delete_assets': 'Assets',
            'archive_asset': 'Assets',
            'restore_asset': 'Assets',
            'view_asset_log': 'Assets',
            'manage_users': 'Administration',
            'manage_roles': 'Administration',
            'import_csv': 'Import',
            'import_suppliers': 'Import',
            'import_locations': 'Import',
            'backup_data': 'Backup',
            'restore_data': 'Backup',
            'view_chart_cost_distribution': 'Dashboard',
            'view_chart_value_development': 'Dashboard',
            'view_chart_asset_status': 'Dashboard',
            'view_chart_delivery_status': 'Dashboard',
            'view_chart_location_map': 'Dashboard',
            'view_chart_categories': 'Dashboard',
            'view_chart_manufacturers': 'Dashboard'
        }

        self.permission_categories = {}
        for perm in perms:
            self.permission_categories[perm.id] = permission_category_map.get(perm.name, 'Sonstiges')

    def grouped_permissions(self):
        groups = {}
        for subfield in self.permissions:
            perm_id = subfield.data
            category = self.permission_categories.get(perm_id, 'Sonstiges')
            groups.setdefault(category, []).append(subfield)

        ordered_groups = []
        for category in self.category_order:
            if category in groups:
                ordered_groups.append((category, sorted(groups.pop(category), key=lambda field: field.label.text.lower())))

        for category in sorted(groups.keys()):
            ordered_groups.append((category, sorted(groups[category], key=lambda field: field.label.text.lower())))

        return ordered_groups


class InventoryCheckForm(FlaskForm):
    """Formular für die Erfassung eines Assets während der Inventur"""
    status = SelectField('Status', choices=[
        ('present', 'Gefunden'),
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
