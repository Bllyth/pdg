from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import IntegerField, SelectField, validators, TextAreaField, FieldList, FormField, StringField, Form
from wtforms.fields.html5 import DateField
from wtforms.validators import Optional, DataRequired

from app import db
from app.models.users import User


class ObjectiveForm(Form):
    objective = TextAreaField('Objective')
    measure_of_success = TextAreaField('Measure of success')
    date_set = DateField('Date Set', validators=[Optional()])
    timeline = StringField('Timeline')
    self_evaluation = TextAreaField('Self Evaluation')
    supervisor_evaluation = TextAreaField('Supervisor Evaluation')


class SupObjectiveForm(FlaskForm):
    objective = TextAreaField('Objective')
    measure_of_success = TextAreaField('Measure of success')
    date_set = DateField('Date Set', validators=[Optional()])
    timeline = StringField('Timeline')
    self_evaluation = TextAreaField('Self Evaluation')
    supervisor_evaluation = TextAreaField('Supervisor Evaluation')


class NextYearObjectiveForm(Form):
    objective = TextAreaField('Objective')
    measure_of_success = TextAreaField('Measure of success')
    timeline = StringField('Timeline')


class ValuesForm(FlaskForm):
    client_focus = TextAreaField('Client Focus')
    boundless = TextAreaField('Boundless')
    collaborate = TextAreaField('Collaborate')
    integrity = TextAreaField('Integrity')
    personal_excellence = TextAreaField('Personal Excellence')


class TrainingForm(Form):
    purpose = TextAreaField('Development Goals/Purpose')
    priority = SelectField('Priority', validate_choice=False,
                           choices=[('', 'Select Training'), ('Critical', 'Critical (C)'), ('Moderate', 'Moderate (M)'),
                                    ('Value Added', 'Value Added (VA)')])
    target_date = DateField('Target date', validators=[Optional()])


class PDGEditForm(FlaskForm):
    date_of_review = DateField('Date of Review', validators=[Optional()])
    review_year = SelectField('Review Year', choices=[('', 'Select Year'), ('2020', '2020'), ('2021', '2021')],
                              validators=[Optional()])


class MainForm(FlaskForm):
    """Parent form."""
    supervisor = StringField('Supervisor')
    department = StringField('Department')
    position = StringField('Position')
    date_of_review = DateField('Date of Review', validators=[Optional()])
    review_year = SelectField('Review Year', choices=[('', 'Select Year'), ('2020', '2020'), ('2021', '2021')], validators=[Optional()])

    employee_feedback = TextAreaField('Feedback')
    supervisor_feedback = TextAreaField('Feedback')
    rating = SelectField('Priority', validate_choice=False,
                         choices=[('', ''), ('Exceeds expectations', 'Exceeds expectations'), ('Above expectations', 'Above expectations'),
                                  ('Meets expectations', 'Meets expectations'), ('Improvement needed', 'Improvement needed'),
                                  ('Unsatisfactory', 'Unsatisfactory')])

    objs = FieldList(
        FormField(ObjectiveForm),
        min_entries=1,
        max_entries=20
    )
    futures = FieldList(
        FormField(NextYearObjectiveForm),
        min_entries=1,
        max_entries=20
    )
    trainings = FieldList(
        FormField(TrainingForm),
        min_entries=1,
        max_entries=20
    )

    def populate_assoc(self, objective_obj):
        i = 0
        for assoc_obj in objective_obj.objective_assoc:
            assoc_obj.objective_id = self.objs[i].data

            i +=1