from flask_wtf import FlaskForm
from wtforms import (
    StringField, TextAreaField, SelectField, IntegerField, 
    RadioField, FieldList, FormField, BooleanField, DateField,
    HiddenField
)
from wtforms.validators import DataRequired, Optional, Length
from datetime import datetime, timedelta

class WizardStep1Form(FlaskForm):
    """Formular für Schritt 1: Lieferant und Standort Auswahl"""
    supplier_id = RadioField('Lieferant', validators=[DataRequired()], coerce=int, choices=[])
    location = SelectField('Standort', validators=[DataRequired()], coerce=int, choices=[])

class AssetSelectionForm(FlaskForm):
    """Formular für ein einzelnes Asset in der Auswahlliste"""
    asset_id = HiddenField('Asset ID')
    select = BooleanField('Auswählen')
    quantity = IntegerField('Menge', default=1)
    serial_number = StringField('Seriennummer', validators=[Optional(), Length(max=100)])

class WizardStep2Form(FlaskForm):
    """Formular für Schritt 2: Asset-Auswahl mit Filtern"""
    # Filterfelder
    filter_name = StringField('Name', validators=[Optional()])
    filter_category = SelectField('Kategorie', coerce=int)
    filter_manufacturer = SelectField('Hersteller', coerce=int)
    
    # Liste der Assets
    assets = FieldList(FormField(AssetSelectionForm))
    
    # Aktionsbuttons
    action = HiddenField('Aktion')

class WizardStep3Form(FlaskForm):
    """Formular für Schritt 3: Details und Versandinformationen"""
    tracking_number = StringField('Sendungsverfolgungsnummer', validators=[Optional(), Length(max=50)])
    tracking_carrier = SelectField('Paketdienst', choices=[
        ('none', 'Ohne Paketdienst'),
        ('dhl', 'DHL'),
        ('ups', 'UPS'),
        ('fedex', 'FedEx'),
        ('hermes', 'Hermes'),
        ('dpd', 'DPD'),
        ('gls', 'GLS'),
        ('post', 'Deutsche Post')
    ])
    expected_delivery_date = DateField('Geplantes Lieferdatum', validators=[Optional()], 
                                      default=datetime.now() + timedelta(days=5))
    comment = TextAreaField('Kommentar', validators=[Optional(), Length(max=500)])

class WizardStep4Form(FlaskForm):
    """Formular für Schritt 4: Bestellung bestätigen"""
    action = HiddenField('Aktion', default="save")
    # Mögliche Aktionen: save (nur speichern), send_email (speichern und E-Mail senden), import (speichern und Assets importieren)
