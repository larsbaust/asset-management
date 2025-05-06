from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FormField, FieldList, IntegerField, BooleanField, HiddenField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, NumberRange

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
