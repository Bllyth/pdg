from io import BytesIO

from flask import render_template, url_for, flash, redirect, request, send_file
from flask_dance.contrib.azure import azure
from flask_login import login_required, current_user
import pandas as pd
from oauthlib.oauth2 import TokenExpiredError

from . import main
from .forms import ObjectiveForm, MainForm, NextYearObjectiveForm, ValuesForm, TrainingForm
from .. import db
from ..models.pdg import PDG, Objective, NextYearObjective, Values, Training
from ..models.users import User



# def send_email(message):
#     credentials = (Config.CLIENT_ID, Config.CLIENT_SECRET)
#     account = Account(credentials, auth_flow_type='credentials', tenant_id=Config.TENANT_ID)
#     if account.authenticate():
#         print(' Authenticated!')
#     m = account.new_message(resource='bb1support@wiocc.net')
#     m.to.add('w.systems@wiocc.net')
#     m.subject = 'Claim module Netsuite Error'
#     m.body = message
#     m.send()


@main.route('/', methods=['GET', 'POST'])
@login_required
def pdgs():
    # global all_pdgs
    # if not azure.authorized:
    #     return redirect(url_for('azure.login'))

    if current_user.position == 'Human Resources Manager':
        current_user.role_id = 3
        db.session.commit()

        all_pdg = PDG.query.all()
    else:



        all_pdg = PDG.query.filter_by(supervisor_id=current_user.id).all()
        if all_pdg:
            current_user.role_id = 2
        else:
            all_pdg = PDG.query.filter_by(user_id=current_user.id).all()


    return render_template('pdg/all_pdgs.html', all_pdg=all_pdg)


@main.route('/new-pdg', methods=['GET', 'POST'])
@login_required
def new_pdg():
    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm(prefix='values-_-')
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')

    supervisor = User.query.filter_by(email=current_user.supervisor).first()

    form = MainForm(supervisor=supervisor.username)

    if form.validate():
        new_pdg = PDG(
            date_of_review=form.date_of_review.data,
            review_year=form.review_year.data,
            employee_feedback=form.employee_feedback.data,
            user_id=current_user.id,
            supervisor_id=supervisor.id
        )
        #     supervisor_feedback=form.supervisor_feedback.data,
        #     raing=form.rating.data
        # )

        db.session.add(new_pdg)

        for objective in form.objs.data:
            new_objective = Objective(**objective)

            new_pdg.objectives.append(new_objective)

            print(objective)

        for future in form.futures.data:
            new_future = NextYearObjective(**future)
            new_pdg.futures.append(new_future)

            print(future)

        for value in form.values.data:
            new_value = Values(**value)
            new_pdg.values.append(new_value)
            print(value)

        for training in form.trainings.data:
            new_training = Training(**training)
            new_pdg.trainings.append(new_training)
            print(training)

        if request.form['btn'] == 'submit':
            new_pdg.status = True
            db.session.commit()

            flash("PDG Added successfully", 'success')
            # return redirect(url_for('main.pdg', pdg_id=new_pdg.id))

        db.session.commit()

        flash("PDG saved successfully", 'success')
        return redirect(url_for('main.pdg', pdg_id=new_pdg.id, supervisor=supervisor.username))

    else:
        print(form.errors)
        # flash("An error occurred", 'warning')

    return render_template('pdg/new.html', form=form, objective_form=objective_form, future_form=future_form,
                           training_form=training_form, values_form=values_form)


@main.route('/pdg/<int:pdg_id>', methods=['GET', 'POST'])
@login_required
def pdg(pdg_id):
    form = MainForm()
    pdg = PDG.query.filter_by(id=pdg_id).first()
    if form.validate_on_submit():
        pdg.supervisor_feedback = form.supervisor_feedback.data
        pdg.rating = form.rating.data
        if request.form.get('approve'):
            print('Hello')
            pdg.approval_status = True

        db.session.commit()

        flash("PDG approved successfully", 'success')
    else:
        print(form.errors)

    return render_template('pdg/pdg.html', pdg=pdg, form=form)


@main.route('/pdg/edit/<int:pdg_id>', methods=['GET', 'POST'])
@login_required
def pdg_edit(pdg_id):
    pdg = PDG.query.filter_by(id=pdg_id).first()

    objectives = Objective.query.filter_by(pdg_id=pdg.id).all()

    future = NextYearObjective.query.filter_by(pdg_id=pdg.id).all()
    training = Training.query.filter_by(pdg_id=pdg.id).all()
    values = Values.query.filter_by(pdg_id=pdg.id).all()

    supervisor = User.query.filter_by(id=pdg.user_id).first()

    form = MainForm(data={'supervisor': supervisor.username,
                          'review_year': pdg.review_year, 'objs': objectives, 'futures': future,
                          'trainings': training, 'values': values})

    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm(prefix='values-_-')
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')

    # objectives = Objective.query.filter_by(pdg_id=pdg.id).all()
    # future = NextYearObjective.query.filter_by(pdg_id=pdg.id).all()
    # training = Training.query.filter_by(pdg_id=pdg.id).all()
    # values = Values.query.filter_by(pdg_id=pdg.id).all()
    # form = MainForm(data={'objectives': objectives, 'future': future,
    #                       'training': training, 'values': values})

    # for objective in objectives:
    #     data = {'measure_of_success': objective.measure_of_success}

    # objectivs = [dict(zip(["objective", "measure_of_success"], objective)) for objective in objectives]
    #
    # for objective in objectivs:
    #     form.objs.append_entry(objective)

    # data_in = []
    # for obj_obj in pdg.
    # form = MainForm()
    # objs = []
    # for idx, objective in enumerate(objectives):
    #     print(objective)
    #     obj_form = ObjectiveForm()
    #     obj_form.objective = objective.objective
    #     obj_form.measure_of_success = objective.measure_of_success
    #     obj_form.date_set = objective.date_set
    #     obj_form.timeline = objective.timeline
    #     obj_form.self_evaluation = objective.self_evaluation
    #     obj_form.supervisor_evaluation = objective.supervisor_evaluation

    # form.objs.append_entry(obj_form)
    #
    #     objs.append({'objective': objective.objective})

    # if request.method == 'GET':

    # if form.validate():
    #     pdg.date_of_review = form.date_of_review.data,
    #     pdg.review_year = form.review_year.data,
    #     pdg.employee_feedback = form.employee_feedback.data

    # for objective in form.objectives.data:
    #     new_objective = Objective(**objective)
    #
    #     new_pdg.objectives.append(new_objective)
    #
    #     print(objective)
    #
    # for future in form.futures.data:
    #     new_future = NextYearObjective(**future)
    #     new_pdg.futures.append(new_future)
    #
    #     print(future)
    #
    # for value in form.values.data:
    #     new_value = Values(**value)
    #     new_pdg.values.append(new_value)
    #     print(value)
    #
    # for training in form.trainings.data:
    #     new_training = Training(**training)
    #     new_pdg.trainings.append(new_training)
    #     print(training)
    #
    # if request.form['btn'] == 'submit':
    #     new_pdg.status = True
    #     db.session.commit()

    return render_template('pdg/new.html', pdg=pdg, form=form, objective_form=objective_form,
                           future_form=future_form,
                           training_form=training_form, values_form=values_form)


@main.route('/export')
@login_required
def export():
    output = BytesIO()

    df = pd.read_sql(
        sql="select u.username as 'Employee Name', u.position as 'Current Position', review_year as 'Review Period', employee_feedback as 'Overall Feedback from Employee', supervisor_feedback as 'Overall Feedback from Supervisor', rating as 'Overall Rating' from dbo.pdg inner join users s on s.id = pdg.supervisor_id inner join users u on u.id = pdg.user_id",
        con=db.session.bind)

    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, 'data', index=False)
    # elif type == 'csv':
    #     df.to_csv(writer, 'data', index=False)
    writer.save()
    output.seek(0)
    return send_file(output, attachment_filename='export.xlsx', as_attachment=True)


@main.route("/users")
@login_required
def users():
    # if not azure.authorized:
    #     return redirect(url_for("azure.login"))
    # try:
    #     resp = azure.get("/v1.0/users")
    #     print(resp)
    #     assert resp.ok
    # except TokenExpiredError as e:
    #     return redirect(url_for("azure.login"))
    resp = azure.get("/v1.0/me")

    azure_infos = resp.json()
    #
    print('Hello', azure_infos['value'])

    return 'Hello'
