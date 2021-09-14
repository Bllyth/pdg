from app import db


class PDG(db.Model):
    __tablename__ = 'pdg'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    supervisor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date_of_review = db.Column(db.String)
    review_year = db.Column(db.String)
    employee_feedback = db.Column(db.String)
    supervisor_feedback = db.Column(db.String)
    rating = db.Column(db.String)
    status = db.Column(db.Boolean, default=False)
    approved = db.Column(db.Boolean, default=False)

    pdg_user = db.relationship(
        'User', foreign_keys=[user_id],
        backref=db.backref('pdgs', lazy='dynamic', collection_class=list)
    )
    pdg_supervisor = db.relationship(
            'User', foreign_keys=[supervisor_id],
            backref=db.backref('supervisors', lazy='dynamic', collection_class=list)
        )


class Objective(db.Model):
    __tablename__ = 'objectives'

    id = db.Column(db.Integer, primary_key=True)
    pdg_id = db.Column(db.Integer, db.ForeignKey('pdg.id'))
    objective = db.Column(db.String)
    measure_of_success = db.Column(db.String)
    date_set = db.Column(db.DateTime)
    timeline = db.Column(db.String)
    self_evaluation = db.Column(db.String)
    supervisor_evaluation = db.Column(db.String)

    pdg = db.relationship(
        'PDG',
        backref=db.backref('objectives', lazy='dynamic', collection_class=list)
    )


class NextYearObjective(db.Model):
    __tablename__ = 'next_year_objectives'

    id = db.Column(db.Integer, primary_key=True)
    pdg_id = db.Column(db.Integer, db.ForeignKey('pdg.id'))
    objective = db.Column(db.String)
    measure_of_success = db.Column(db.String)
    timeline = db.Column(db.String)

    pdg_future = db.relationship(
        'PDG',
        backref=db.backref('futures', lazy='dynamic', collection_class=list)
    )


class Values(db.Model):
    __tablename__ = 'values'

    id = db.Column(db.Integer, primary_key=True)
    pdg_id = db.Column(db.Integer, db.ForeignKey('pdg.id'))
    client_focus = db.Column(db.String)
    boundless = db.Column(db.String)
    collaborate = db.Column(db.String)
    integrity = db.Column(db.String)
    personal_excellence = db.Column(db.String)

    pdg_value = db.relationship(
        'PDG',
        backref=db.backref('values', lazy='dynamic', collection_class=list)
    )


class Training(db.Model):
    __tablename__ = 'training'

    id = db.Column(db.Integer, primary_key=True)
    pdg_id = db.Column(db.Integer, db.ForeignKey('pdg.id'))
    purpose = db.Column(db.String)
    priority = db.Column(db.String)
    target_date = db.Column(db.DateTime)

    pdg_training = db.relationship(
        'PDG',
        backref=db.backref('trainings', lazy='dynamic', collection_class=list)
    )
