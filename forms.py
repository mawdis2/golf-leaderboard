from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length

class TournamentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    date = DateField('Date', validators=[DataRequired()])
    course = SelectField('Course', coerce=int, validators=[DataRequired()])
    has_individual_matches = BooleanField('Individual Matches Tournament')

class CourseForm(FlaskForm):
    course_name = StringField('Course Name', validators=[DataRequired()])
    submit = SubmitField('Add Course') 