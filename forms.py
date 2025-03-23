from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length

class TournamentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    date = DateField('Date', validators=[DataRequired()])
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    has_individual_matches = BooleanField('Individual Matches Tournament') 