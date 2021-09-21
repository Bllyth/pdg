from datetime import datetime
from io import BytesIO
from itertools import chain

from O365 import Account
from flask import render_template, url_for, flash, redirect, request, send_file
from flask_dance.contrib.azure import azure
from flask_login import login_required, current_user
import pandas as pd
from flask_weasyprint import render_pdf
from weasyprint import HTML
from oauthlib.oauth2 import TokenExpiredError
from sqlalchemy import or_

from . import main
from .forms import ObjectiveForm, MainForm, NextYearObjectiveForm, ValuesForm, TrainingForm, PDGEditForm
from .. import db
from ..models.pdg import PDG, Objective, NextYearObjective, Values, Training
from ..models.users import User
from config import Config


def send_email(message, user):
    credentials = ('fffbcbe3-c387-4745-a85a-6c7083313a20', 'hG_7MRT6~gza9IAUw.CFN.Zb4okSez2y6~')
    account = Account(credentials, auth_flow_type='credentials', tenant_id='84cba236-0ee0-4481-bf46-8016d81056fa')
    if account.authenticate():
        print(' Authenticated!')
    m = account.new_message(resource='bb1support@wiocc.net')
    m.to.add(user)
    m.subject = 'PDG'
    m.body = message
    m.send()


def check_users_below_supervisor(supervisor_email, pdg_id):
    # users = Get all users with supervisor_id as the supervisor
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id, id=pdg_id).first()

        if pdg:
            return pdg
        pdg = check_users_below_supervisor(user.email, pdg_id)
        if pdg:
            return pdg
    return None


def get_pdgs_below_supervisor(supervisor_email, pdgs):
    # users = Get all users with supervisor_id as the supervisor
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id, status=True).all()

        if pdg:
            pdgs.append(pdg)
        pdgs = get_pdgs_below_supervisor(user.email, pdgs)
    return pdgs


@main.before_request
@login_required
def user_role():
    if current_user.position == 'Human Resources Manager':
        current_user.role_id = 3

    user = User.query.filter_by(email=current_user.supervisor).first()
    user.role_id = 2

    db.session.commit()


@main.route('/', methods=['GET', 'POST'])
@login_required
def pdgs():
    if current_user.role_id == 3:
        all_pdgs = PDG.query.filter_by(status=True).all()
    elif current_user.role_id == 2:
        pdgs = []
        pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

        pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

        all_pdgs = list(chain(*pdgs))

    else:
        all_pdgs = PDG.query.filter_by(user_id=current_user.id).all()

    return render_template('pdg/all_pdgs.html', all_pdg=all_pdgs)


@main.route('/new-pdg', methods=['GET', 'POST'])
@login_required
def new_pdg():
    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm()
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')

    supervisor = User.query.filter_by(email=current_user.supervisor).first()
    now = datetime.utcnow()
    form = MainForm(review_year=now.year, date_of_review=now)

    if request.method == 'GET':
        form.supervisor.data = supervisor.username
        form.department.data = current_user.department
        form.position.data = current_user.position

    if form.validate():
        new_pdg = PDG(
            date_of_review=form.date_of_review.data,
            review_year=form.review_year.data,
            employee_feedback=form.employee_feedback.data,
            user_id=current_user.id,
            supervisor_id=supervisor.id
        )

        db.session.add(new_pdg)
        db.session.flush()

        new_values = Values(
            pdg_id=new_pdg.id,
            client_focus=values_form.client_focus.data,
            boundless=values_form.boundless.data,
            collaborate=values_form.collaborate.data,
            integrity=values_form.integrity.data,
            personal_excellence=values_form.personal_excellence.data
        )

        db.session.add(new_values)

        for objective in form.objs.data:
            new_objective = Objective(**objective)

            new_pdg.objectives.append(new_objective)

        for future in form.futures.data:
            new_future = NextYearObjective(**future)
            new_pdg.futures.append(new_future)

        for training in form.trainings.data:
            new_training = Training(**training)
            new_pdg.trainings.append(new_training)

        if request.form['btn'] == 'submit':
            new_pdg.status = True
            db.session.commit()

            flash("PDG Added successfully", 'success')

        db.session.commit()

        flash("PDG saved successfully", 'success')
        return redirect(url_for('main.pdg', pdg_id=new_pdg.id, supervisor=supervisor.username))

    # else:
    #     print(form.errors)

    return render_template('pdg/new.html', form=form, objective_form=objective_form, future_form=future_form,
                           training_form=training_form, values_form=values_form)


@main.route('/pdg/<int:pdg_id>', methods=['GET', 'POST'])
@login_required
def pdg(pdg_id):
    form = MainForm()
    objective_form = ObjectiveForm()
    pdg_edit = PDGEditForm()

    pdg = PDG.query.filter_by(id=pdg_id, user_id=current_user.id).first()

    if not pdg:
        if current_user.role_id == 3:
            pdg = PDG.query.filter_by(id=pdg_id, approved=True).first()

        elif current_user.role_id == 2:
            pdg = check_users_below_supervisor(current_user.email, pdg_id)

    # print(pdg)
    if pdg:

        value = Values.query.filter_by(id=pdg_id).first()
        supervisor = User.query.filter_by(email=current_user.supervisor).first()

        if request.method == 'GET':
            form.supervisor.data = supervisor.username
            form.department.data = current_user.department
            form.position.data = current_user.position
            # pdg_edit.review_year.data = pdg.review_year
            # pdg_edit.date_of_review.data = pdg.date_of_review
            # form.supervisor_feedback.data = pdg.supervisor_feedback
            # form.rating.data = pdg.rating

        if request.method == 'POST':

            if form.validate_on_submit():
                pdg.supervisor_feedback = form.supervisor_feedback.data
                pdg.rating = form.rating.data
                # pdg.date_of_review = form.date_of_review.data
                # pdg.review_year = form.review_year.data

                if request.form['btn'] == 'reject':
                    pdg.status = False
                    db.session.commit()

                    send_email(message='Your PDG was rejected', user=pdg.pdg_user.email)
                    send_email(message='Your have rejected a PDG', user=current_user.email)

                    flash("PDG rejected successfully", 'success')

                    return redirect(url_for('main.pdgs'))

                if request.form['btn'] == 'approve':
                    pdg.approved = True
                    db.session.commit()

                    send_email(message='Your PDG was approved', user=pdg.pdg_user.email)
                    send_email(message='Your have approved a PDG', user=current_user.email)

                    flash("PDG approved successfully", 'success')

                db.session.commit()

                flash("PDG saved successfully", 'success')

                return redirect(url_for('main.pdg', pdg_id=pdg.id))
            else:
                print(form.errors)

        return render_template('pdg/pdg.html', pdg=pdg, value=value, form=form, pdg_edit=pdg_edit,
                            objective_form=objective_form)
    return 'None'


@main.route('/pdg/edit/<int:pdg_id>', methods=['GET', 'POST'])
@login_required
def pdg_edit(pdg_id):
    pdg = PDG.query.filter_by(id=pdg_id).first()

    objectives = Objective.query.filter_by(pdg_id=pdg.id).all()

    future = NextYearObjective.query.filter_by(pdg_id=pdg.id).all()
    training = Training.query.filter_by(pdg_id=pdg.id).all()
    value = Values.query.filter_by(pdg_id=pdg.id).first()
    supervisor = User.query.filter_by(email=current_user.supervisor).first()

    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm()
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')
    form = MainForm()

    if request.method == 'GET':
        form = MainForm(data={'objs': objectives, 'futures': future,
                              'trainings': training})
        form.employee_feedback.data = pdg.employee_feedback
        form.supervisor_feedback.data = pdg.supervisor_feedback
        form.rating.data = pdg.rating
        form.review_year.data = pdg.review_year
        form.supervisor.data = supervisor.username
        form.department.data = current_user.department
        form.position.data = current_user.position
        form.date_of_review.data = pdg.date_of_review
        values_form.client_focus.data = value.client_focus
        values_form.boundless.data = value.boundless
        values_form.collaborate.data = value.collaborate
        values_form.integrity.data = value.integrity
        values_form.personal_excellence.data = value.personal_excellence

    if form.validate():
        new_pdg = PDG(
            date_of_review=form.date_of_review.data,
            review_year=form.review_year.data,
            employee_feedback=form.employee_feedback.data,
            user_id=current_user.id,
            supervisor_id=supervisor.id
        )

        db.session.add(new_pdg)
        db.session.flush()

        new_values = Values(
            pdg_id=new_pdg.id,
            client_focus=values_form.client_focus.data,
            boundless=values_form.boundless.data,
            collaborate=values_form.collaborate.data,
            integrity=values_form.integrity.data,
            personal_excellence=values_form.personal_excellence.data
        )
        #     supervisor_feedback=form.supervisor_feedback.data,
        #     raing=form.rating.data
        # )

        db.session.add(new_values)

        for objective in form.objs.data:
            new_objective = Objective(**objective)

            new_pdg.objectives.append(new_objective)

            print(objective)

        for future in form.futures.data:
            new_future = NextYearObjective(**future)
            new_pdg.futures.append(new_future)

            print(future)

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

@main.route("/print/<pdg_id>")
@login_required
def print_pdg(pdg_id):
    form = MainForm()
    objective_form = ObjectiveForm()
    pdg_edit = PDGEditForm()

    pdg = PDG.query.filter_by(id=pdg_id).first()
    user = User.query.filter_by(id=pdg.user_id).first()

    value = Values.query.filter_by(id=pdg_id).first()
    supervisor = User.query.filter_by(email=current_user.supervisor).first()

    html = render_template('print/print.html', pdg=pdg, user=user, value=value, supervisor=supervisor)
    if pdg.user_id == current_user.id:
        return render_pdf(HTML(string=html, base_url='.'))

