from datetime import datetime

from app import create_app, db
from app.models.users import User
from app.models.pdg import PDG

app = create_app()


# Sg3WP4ht
#
# n6iE8%QH

@app.cli.command()
def is_hr():
    user = User.query.filter_by(email='leonard.muriithi@wiocc.net').first()
    user.is_hr = True
    db.session.commit()


@app.cli.command()
def approve_pdg():
    pdg = PDG.query.filter_by(id=43).first()
    pdg.approved = True
    db.session.commit()
    print('PDG approved')


@app.cli.command()
def pdg():
    user = User.query.filter_by(email='marios.phillips@wiocc.net').first()
    supervisor = User.query.filter_by(email='susan.collins@wiocc.net').first()
    pdg = PDG.query.filter_by(user_id=user.id).first()

    pdg.supervisor_id = supervisor.id


@app.cli.command()
def status():
    supervisor = User.query.filter_by(email='jason.tutty@wiocc.net').first()
    pdgs = PDG.query.filter_by(supervisor_id=supervisor.id).all()

    for pdg in pdgs:
        user = User.query.filter_by(id=pdg.user_id).first()
        print(user.username, user.pdg_status, pdg.pdg_status, )

    # users = User.query.filter_by().all()
    # for user in users:
    #     for pdg in pdgs:
    #         if pdg.approved == False and pdg.user_id == user.id:
    #             pdg.pdg_status = 'Pending Submission'
    #             user.pdg_status = 'Pending Submission'
    #         elif pdg.approved == True and pdg.user_id == user.id:
    #             pdg.pdg_status = 'Approved'
    #             user.pdg_status = 'Approved'
    #         if pdg.user_id == user.id:
    #             user.has_pdg = True
    #
    #         db.session.commit()


@app.cli.command()
def roles():
    from app.models.users import Role
    role = Role(name='User')
    role2 = Role(name='Supervisor')
    role3 = Role(name='HR')

    db.session.add_all([role, role2, role3])
    db.session.commit()


@app.cli.command()
def users():
    # supervisor = User.query.filter_by(email='joel.mieni@wiocc.net').first()
    user = User.query.filter_by(email='christiaan.smith@wiocc.net').first()
    pdg = PDG.query.filter_by(id=72).first()
    # print(user.supervisor)
    # print(pdg.supervisor_id)

    user.pdg_status = 'Pending Submission'
    pdg.status = False
    db.session.commit()

    print(pdg.status)
    print(user.pdg_status)


@app.cli.command()
def insert():
    from app.models.users import User
    from app.models.pdg import PDG, Objective
    user = User.query.filter_by(email='wyclife.momanyi@wiocc.net').first()
    pdg = PDG.query.filter_by(user_id=user.id).first()

    print(pdg.id, pdg.review_year)

    objective = 'Escalation/Fault Management'
    measure = '-Continue to be more proactive and timelier in both accepting escalations and solving incidents-Provide constant updates on TEAMS for the management team to follow on the troubleshooting.'
    timeline = 'Q2'
    d = '11/10/2020 1:05:00 PM'
    date = datetime.strptime(str(d), '%Y-%m-%d %H:%M:%S').date()

    objective = Objective(
        objective=objective,
        measure_of_success=measure,
        timeline=timeline,
        date_set=date,
        pdg_id=pdg.id,

    )

    db.session.add(objective)
    db.session.commit()

    print(objective.date_set)


@app.cli.command()
def insert():
    users = User.query.filter_by(has_pdg=True).all()

    print(len(users))
