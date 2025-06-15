from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, Email, URL

class SupplierForm(FlaskForm):
    """Formular zur Bearbeitung und Erstellung von Lieferanten"""
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=100)])
    address = TextAreaField('Adresse', validators=[Optional(), Length(max=255)])
    phone = StringField('Telefon', validators=[Optional(), Length(max=50)])
    email = StringField('E-Mail', validators=[Optional(), Email(), Length(max=100)])
    website = StringField('Website', validators=[Optional(), URL(), Length(max=100)])
    contact_name = StringField('Ansprechpartner', validators=[Optional(), Length(max=100)])
    customer_number = StringField('Kundennummer', validators=[Optional(), Length(max=50)])
    creditor_number = StringField('Kreditorennummer', validators=[Optional(), Length(max=50)])
    submit = SubmitField('Speichern')
