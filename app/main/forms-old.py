from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import TextAreaField, StringField, SelectField, FormField, SubmitField, FieldList, Form, validators, \
    IntegerField
from wtforms.fields.html5 import DateField
from wtforms.validators import Optional


class NullableDateField(DateField):
    """Native WTForms DateField throws error for empty dates.
    Let's fix this so that we could have DateField nullable."""

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = ' '.join(valuelist).strip()
            if date_str == '':
                self.data = None
                return
            try:
                self.data = datetime.strptime(date_str, self.format).date()
            except ValueError:
                self.data = None
                # raise ValueError(self.gettext('Not a valid date value'))


class NonValidatingSelectField(SelectField):
    def pre_validate(self, form):
        pass


class ObjectiveForm(Form):
    objective = TextAreaField('Objective')
    measure_of_success = TextAreaField('Measure of success')
    date_set = DateField('Date Set')
    timeline = StringField('Timeline')
    self_evaluation = TextAreaField('Self Evaluation')
    supervisor_evaluation = TextAreaField('Supervisor Evaluation')


class NextYearObjectiveForm(Form):
    objective = TextAreaField('Objective')
    measure_of_success = TextAreaField('Measure of success')
    timeline = StringField('Timeline')


class ValuesForm(Form):
    client_focus = TextAreaField('Client Focus')
    boundless = TextAreaField('Boundless')
    collaborate = TextAreaField('Collaborate')
    integrity = TextAreaField('Integrity')
    personal_excellence = TextAreaField('Personal Excellence')


class TrainingForm(Form):
    purpose = TextAreaField('Development Goals/Purpose')
    priority = SelectField('Priority', validate_choice=False,
                           choices=[('', ''), ('C', 'Critical (c)'), ('M', 'Moderate (M)'),
                                    ('VA', 'Value Added (VA)')])
    target_date = DateField('Target date')


class EmployeeFeedbackForm(Form):
    feedback = TextAreaField('Objective')


class SupervisorFeedbackForm(Form):
    feedback = TextAreaField('Objective')
    rating = SelectField('Priority', validate_choice=False,
                         choices=[('', ''), ('exceeds', 'Exceeds expectations'), ('above', 'Above expectations'),
                                  ('meets', 'Meets expectations'), ('improvement', 'Improvement needed'),
                                  ('unsatisfactory', 'Unsatisfactory')])


class PDGForm(FlaskForm):
    # supervisor = name = QuerySelectField(query_factory=lambda: db.session.query(User).all(), get_label='name')
    # date_of_review = DateField('Date of Review')
    # review_year = SelectField('Review Year', choices=[('', ''), ('2020', '2020'), ('2021', '2021')])

    objectives = FieldList(FormField(ObjectiveForm), min_entries=1, max_entries=20)
    # future_objectives = FieldList(FormField(NextYearObjectiveForm), min_entries=1, max_entries=20)
    # values = FieldList(FormField(ValuesForm), min_entries=1, max_entries=20)
    # training = FieldList(FormField(TrainingForm), min_entries=1, max_entries=20)
    # supervisor_feedback = FieldList(FormField(SupervisorFeedbackForm), min_entries=1, max_entries=20)
    # employee_feedback = FieldList(FormField(EmployeeFeedbackForm), min_entries=1, max_entries=20)

    submit = SubmitField('Submit')



class LapForm(Form):
    """Subform.

    CSRF is disabled for this subform (using `Form` as parent class) because
    it is never used by itself.
    """
    runner_name = StringField(
        'Runner name',
        validators=[validators.InputRequired(), validators.Length(max=100)]
    )
    lap_time = IntegerField(
        'Lap time',
        validators=[validators.InputRequired(), validators.NumberRange(min=1)]
    )
    category = SelectField(
        'Category',
        choices=[('cat1', 'Category 1'), ('cat2', 'Category 2')]
    )
    notes = TextAreaField(
        'Notes',
        validators=[validators.Length(max=255)]
    )


class MainForm(FlaskForm):
    """Parent form."""
    laps = FieldList(
        FormField(LapForm),
        min_entries=1,
        max_entries=20
    )