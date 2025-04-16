from flask_wtf import FlaskForm
from wtforms import SelectField, FormField, FieldList, IntegerField, BooleanField, HiddenField, SubmitField
from wtforms.validators import DataRequired, NumberRange

class AssetOrderForm(FlaskForm):
    class Meta:
        csrf = False
    asset_id = HiddenField()
    select = BooleanField()
    quantity = IntegerField('Menge', default=1, validators=[NumberRange(min=1)])

class OrderPlanForm(FlaskForm):
    supplier = SelectField('Lieferant', coerce=int, validators=[DataRequired()])
    assets = FieldList(FormField(AssetOrderForm))  # KEIN csrf_disabled=True!
    submit = SubmitField('Bestellung erstellen')

from wtforms import TextAreaField

class OrderEditForm(FlaskForm):
    status = SelectField('Status', choices=[('offen', 'offen'), ('bestellt', 'bestellt'), ('erledigt', 'erledigt')], validators=[DataRequired()])
    comment = TextAreaField('Kommentar')
