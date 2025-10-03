from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FormField, FieldList, IntegerField, BooleanField, HiddenField, SubmitField, TextAreaField, DateField, DecimalField
from wtforms.validators import DataRequired, NumberRange, Optional

class AssetOrderForm(FlaskForm):
    class Meta:
        csrf = False
    asset_id = HiddenField()
    select = BooleanField()
    quantity = IntegerField('Menge', default=1, validators=[NumberRange(min=1)])
    serial_number = StringField('Seriennummer (optional)')

class OrderPlanForm(FlaskForm):
    supplier = SelectField('Lieferant', coerce=int, validators=[DataRequired()])
    location = SelectField('Standort', coerce=int, choices=[], validators=[DataRequired()])
    tracking_number = StringField('Sendungsverfolgungsnummer (optional)')
    tracking_carrier = SelectField('Paketdienst', choices=[
        ('', 'Bitte wählen...'),
        ('dhl', 'DHL'),
        ('dpd', 'DPD'),
        ('ups', 'UPS'),
        ('gls', 'GLS'),
        ('hermes', 'Hermes'),
        ('fedex', 'FedEx'),
        ('bpost', 'bpost'),
        ('usps', 'USPS'),
        ('other', 'Andere')
    ])
    # Filterfelder
    filter_name = StringField('Name')
    filter_category = SelectField('Kategorie', coerce=int, choices=[], default=0)
    filter_manufacturer = SelectField('Hersteller', coerce=int, choices=[], default=0)
    filter_assignment = SelectField('Zuordnung', coerce=int, choices=[], default=0)
    assets = FieldList(FormField(AssetOrderForm))
    comment = TextAreaField('Kommentar (optional)')
    submit = SubmitField('Bestellung erstellen')

    def __init__(self, *args, **kwargs):
        super(OrderPlanForm, self).__init__(*args, **kwargs)
        from app.models import Category, Manufacturer, Assignment, Asset
        self.filter_category.choices = [(0, 'Alle Kategorien')] + [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
        self.filter_manufacturer.choices = [(0, 'Alle Hersteller')] + [(m.id, m.name) for m in Manufacturer.query.order_by(Manufacturer.name).all()]
        self.filter_assignment.choices = [(0, 'Alle Zuordnungen')] + [(a.id, a.name) for a in Assignment.query.order_by(Assignment.name).all()]
        # Standorte aus Location-Tabelle holen
        from app.models import Location
        locations = Location.query.order_by(Location.name).all()
        self.location.choices = [(0, 'Standort wählen...')] + [(l.id, l.name) for l in locations]



class OrderEditForm(FlaskForm):
    status = SelectField('Status', choices=[('offen', 'offen'), ('bestellt', 'bestellt'), ('erledigt', 'erledigt')], validators=[DataRequired()])
    tracking_number = StringField('Sendungsverfolgungsnummer (optional)')
    tracking_carrier = SelectField('Paketdienst', choices=[
        ('', 'Bitte wählen...'),
        ('dhl', 'DHL'),
        ('dpd', 'DPD'),
        ('ups', 'UPS'),
        ('gls', 'GLS'),
        ('hermes', 'Hermes'),
        ('fedex', 'FedEx'),
        ('bpost', 'bpost'),
        ('usps', 'USPS'),
        ('other', 'Andere')
    ])
    comment = TextAreaField('Kommentar')
    
# WizardStep Formulare für den Bestellassistenten
class WizardStep1Form(FlaskForm):
    supplier_id = SelectField('Lieferant', coerce=int, validators=[DataRequired()])
    location = SelectField('Standort (optional)', coerce=int)
    budget = DecimalField('Budget (€, optional)', places=2, validators=[Optional()])
    submit = SubmitField('Weiter zu Schritt 2')
    
class WizardStep2Form(FlaskForm):
    filter_name = StringField('Artikelname')
    filter_category = SelectField('Kategorie', coerce=int, default=0)
    filter_manufacturer = SelectField('Hersteller', coerce=int, default=0)
    filter_supplier = SelectField('Lieferant', coerce=int, default=0)
    select_all = BooleanField('Alle auswählen')
    template_id = SelectField('Vorlage laden', coerce=int, choices=[(0, '-- Keine Vorlage --')], default=0)
    load_template = SubmitField('Vorlage laden')
    submit = SubmitField('Weiter zu Schritt 3')
    assets = FieldList(FormField(AssetOrderForm))
    
class WizardStep3Form(FlaskForm):
    tracking_number = StringField('Sendungsverfolgungsnummer (optional)')
    tracking_carrier = SelectField('Paketdienst', choices=[
        ('', 'Bitte wählen...'),
        ('dhl', 'DHL'),
        ('dpd', 'DPD'),
        ('ups', 'UPS'),
        ('gls', 'GLS'),
        ('hermes', 'Hermes'),
        ('fedex', 'FedEx'),
        ('bpost', 'bpost'),
        ('usps', 'USPS'),
        ('other', 'Andere')
    ])
    expected_delivery_date = DateField('Erwartetes Lieferdatum (optional)', validators=[Optional()])
    comment = TextAreaField('Kommentar (optional)')
    submit = SubmitField('Weiter zu Schritt 4')
    
class WizardStep4Form(FlaskForm):
    # Verstecktes Feld für die Aktionsart
    action = HiddenField('Aktion')
    save = SubmitField('Nur speichern')
    send_email = SubmitField('Speichern und E-Mail senden')
    import_assets = SubmitField('Speichern und als Assets importieren')
