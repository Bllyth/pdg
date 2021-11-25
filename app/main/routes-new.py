import logging
from datetime import datetime
from io import BytesIO
import mimetypes
from itertools import chain

import numpy as np
import xlsxwriter
from O365 import Account
from flask import render_template, url_for, flash, redirect, request, send_file, Response
from flask_dance.contrib.azure import azure
from flask_login import login_required, current_user
import pandas as pd
from flask_weasyprint import render_pdf
from weasyprint import HTML
from oauthlib.oauth2 import TokenExpiredError
from sqlalchemy import or_
from werkzeug.datastructures import Headers

from . import main
from .forms import ObjectiveForm, MainForm, NextYearObjectiveForm, ValuesForm, TrainingForm, PDGEditForm
from .. import db
from ..models.pdg import PDG, Objective, NextYearObjective, Values, Training, Log
from ..models.users import User
from config import Config

# logging.basicConfig(filename='error.log', level=logging.DEBUG)


def send_email(subject, message, user):
    credentials = ('fffbcbe3-c387-4745-a85a-6c7083313a20', 'hG_7MRT6~gza9IAUw.CFN.Zb4okSez2y6~')
    account = Account(credentials, auth_flow_type='credentials', tenant_id='84cba236-0ee0-4481-bf46-8016d81056fa')
    if account.authenticate():
        logging.warning('Authenticated!')
    #     print('Authenticated!')

    m = account.new_message(resource='bb1support@wiocc.net')
    m.to.add(user)
    m.subject = subject
    m.body = message
    m.send()


def check_pdgs_of_users_below_supervisor(supervisor_email, pdg_id):
    # users = Get all users with supervisor_id as the supervisor
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        if current_user.is_hr:
            pdg = PDG.query.filter_by(id=pdg_id, approved=True).first()
            if pdg:
                return pdg

        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id, id=pdg_id).first()

        if pdg:
            return pdg
        pdg = check_pdgs_of_users_below_supervisor(user.email, pdg_id)
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


def get_pdgs_status_below_supervisor(supervisor_email, pdgs):
    # users = Get all users with supervisor_id as the supervisor
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id).all()

        if pdg:
            pdgs.append(pdg)
        pdgs = get_pdgs_below_supervisor(user.email, pdgs)
    return pdgs


def get_users_below_supervisor(supervisor_email, users):
    # users = Get all users with supervisor_id as the supervisor
    supervisors = User.query.filter_by(supervisor=supervisor_email).all()
    for supervisor in supervisors:
        user = User.query.filter_by(supervisor=supervisor.email).all()

        if user:
            users.append(user)
        users = get_users_below_supervisor(supervisor.email, users)
    return users


@main.before_request
@login_required
def user_role():
    if current_user.position == 'Human Resources Manager':
        current_user.is_hr = True
    if current_user.position == 'Director, HR and Administration':
        current_user.is_hr = True

    user = User.query.filter_by(email=current_user.supervisor).first()

    user.role_id = 2
    db.session.commit()


@main.route('/', methods=['GET', 'POST'])
@login_required
def pdgs():
    pdg = PDG.query.filter_by(user_id=current_user.id).first()

    if current_user.is_hr == True:
        approved_pdgs = PDG.query.filter_by(approved=True).all()
        pdgs = []

        pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())
        pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

        all_pdgs = list(chain(*pdgs))

        return render_template('pdg/all_pdgs_hr.html', all_pdg=all_pdgs, pdg=pdg, approved_pdgs=approved_pdgs)

    elif current_user.role_id == 2:
        pdgs = []
        pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

        pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

        all_pdgs = list(chain(*pdgs))

    else:
        all_pdgs = PDG.query.filter_by(user_id=current_user.id).all()

    return render_template('pdg/all_pdgs.html', all_pdg=all_pdgs, pdg=pdg)


@main.route('/new-pdg', methods=['GET', 'POST'])
@login_required
def new_pdg():
    now = datetime.utcnow()
    pdg = PDG.query.filter_by(user_id=current_user.id).filter_by(review_year=now.year).first()
    if pdg:
        flash('You already have a pdg for this year', 'warning')
        return redirect(url_for('main.pdgs'))
    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm()
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')

    supervisor = User.query.filter_by(email=current_user.supervisor).first()

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

        current_user.has_pdg = True
        current_user.pdg_status = 'Pending Submission'

        if request.form['btn'] == 'submit':
            new_pdg.status = True
            current_user.pdg_status = 'Pending Approval'
            send_email(subject='PDG Submitted',
                       message=f'{current_user.username} has submitted their PDG. {url_for("main.pdg", pdg_id=new_pdg.id)}',
                       user=pdg.pdg_user.email)
            # db.session.commit()
            log = Log(
                user_id=current_user.id,
                pdg_id=new_pdg.id,
                action='Created PDG'
            )
            db.session.add(log)

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
        if current_user.is_hr:
            pdg = check_pdgs_of_users_below_supervisor(current_user.email, pdg_id)

        if current_user.role_id == 2:
            pdg = check_pdgs_of_users_below_supervisor(current_user.email, pdg_id)

    if pdg:
        # print(objective_form.supervisor_evaluation.data)
        value = Values.query.filter_by(pdg_id=pdg.id).first()
        supervisor = User.query.filter_by(id=pdg.supervisor_id).first()
        user = User.query.filter_by(id=pdg.user_id).first()

        if request.method == 'GET':
            form.supervisor.data = supervisor.username
            form.department.data = current_user.department
            form.position.data = user.position
            # pdg_edit.review_year.data = pdg.review_year
            # pdg_edit.date_of_review.data = pdg.date_of_review
            form.supervisor_feedback.data = pdg.supervisor_feedback
            form.rating.data = pdg.rating

        if request.method == 'POST':
            # print('Evaluation', objective_form.supervisor_evaluation.data)

            if form.validate_on_submit():

                # pdg.date_of_review = form.date_of_review.data
                # pdg.review_year = form.review_year.data

                if request.form['btn'] == 'reject':
                    pdg.status = False
                    user.pdg_status = 'Rejected'
                    log = Log(
                        user_id=current_user.id,
                        pdg_id=pdg.id,
                        action='Rejected PDG'
                    )
                    db.session.add(log)
                    db.session.commit()

                    send_email(subject='Your PDG was rejected',
                               message=f'{current_user.username} has rejected your PDG. Please click on the link below to access the pdg record.{url_for("main.pdg", pdg_id=pdg.id, _external=True)}',
                               user=pdg.pdg_user.email)

                    send_email(subject='You have rejected a PDG',
                               message=f"You have rejected {pdg.pdg_user.username}'s PDG. Please click on the link below to access the pdg record.{url_for('main.pdg', pdg_id=pdg.id, _external=True)}",
                               user=current_user.email)

                    flash("PDG rejected successfully", 'success')

                    return redirect(url_for('main.pdgs'))

                if request.form['btn'] == 'approve':
                    user.pdg_status = 'Approved'
                    log = Log(
                        user_id=current_user.id,
                        pdg_id=pdg.id,
                        action='Approved PDG'
                    )
                    db.session.add(log)

                    pdg.approved = True
                    db.session.commit()

                    send_email(subject='Your PDG was approved',
                               message=f'{current_user.username} has approve your PDG. Please click on the link below to access the pdg record.{url_for("main.pdg", pdg_id=pdg.id, _external=True)}',
                               user=pdg.pdg_user.email)

                    send_email(subject='You have approved a PDG',
                               message=f"You have approved {pdg.pdg_user.username}'s PDG. Please click on the link below to access the pdg record.{url_for('main.pdg', pdg_id=pdg.id, _external=True)}",
                               user=current_user.email)

                    flash("PDG approved successfully", 'success')
                    return redirect(url_for('main.pdgs'))

                if request.form['btn'] == 'submit':
                    user.pdg_status = 'Pending Approval'
                    log = Log(
                        user_id=current_user.id,
                        pdg_id=pdg.id,
                        action='Submitted PDG'
                    )
                    db.session.add(log)
                    pdg.status = True
                    db.session.commit()

                    flash('Pdg submitted successfully', 'success')

                    send_email(subject='You submitted your PDG',
                               message=f'You have submitted your PDG for review. {url_for("main.pdg", pdg_id=pdg.id, _external=True)}',
                               user=pdg.pdg_user.email)

                    send_email(subject='You have  a new PDG to approve',
                               message=f"{pdg.pdg_user.username} has submitted their PDG. {url_for('main.pdg', pdg_id=pdg.id, _external=True)}",
                               user=pdg.pdg_user.supervisor)

                    return redirect(url_for('main.pdgs'))

                for objective in pdg.objectives:
                    objective.supervisor_evaluation = request.form[str(objective.id)]

                pdg.supervisor_feedback = form.supervisor_feedback.data
                pdg.rating = form.rating.data

                db.session.commit()

                flash("PDG saved successfully", 'success')

                return redirect(url_for('main.pdg', pdg_id=pdg.id))
            # else:
            #     print(form.errors)

        return render_template('pdg/pdg.html', pdg=pdg, value=value, form=form, pdg_edit=pdg_edit,
                               objective_form=objective_form, user=user)
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
        if value:
            values_form.client_focus.data = value.client_focus
            values_form.boundless.data = value.boundless
            values_form.collaborate.data = value.collaborate
            values_form.integrity.data = value.integrity
            values_form.personal_excellence.data = value.personal_excellence

    if form.validate():
        if value:
            value.client_focus = values_form.client_focus.data
            value.boundless = values_form.boundless.data
            value.collaborate = values_form.collaborate.data
            value.integrity = values_form.integrity.data
            value.personal_excellence = values_form.personal_excellence.data,
        else:
            values = Values(
                pdg_id=pdg.id,
                client_focus=values_form.client_focus.data,
                boundless=values_form.boundless.data,
                collaborate=values_form.collaborate.data,
                integrity=values_form.integrity.data,
                personal_excellence=values_form.personal_excellence.data
            )
            db.session.add(values)

        pdg.employee_feedback = form.employee_feedback.data,
        pdg.date_of_review = form.date_of_review.data
        # print(value.client_focus)

        for obj in objectives:
            db.session.delete(obj)

        for objective in form.objs.data:
            if objective['date_set'] == None:
                objective['date_set'] = ''
            new_objective = Objective(**objective)
            pdg.objectives.append(new_objective)

        for ft in future:
            db.session.delete(ft)

        for future in form.futures.data:
            new_future = NextYearObjective(**future)
            pdg.futures.append(new_future)

        for tr in training:
            db.session.delete(tr)

        for training in form.trainings.data:
            # print(form.trainings.data)
            if training['target_date'] == None:
                training['target_date'] = ''
            if training['priority'] == None:
                training['target_date'] = ''
            new_training = Training(**training)
            pdg.trainings.append(new_training)

        if request.form['btn'] == 'submit':
            pdg.status = True
            db.session.commit()

            flash("PDG Added successfully", 'success')
            return redirect(url_for('main.pdg', pdg_id=pdg.id))

        db.session.commit()

        flash("PDG saved successfully", 'success')
        return redirect(url_for('main.pdg', pdg_id=pdg.id, supervisor=supervisor.username))

    return render_template('pdg/new.html', pdg=pdg, form=form, objective_form=objective_form,
                           future_form=future_form,
                           training_form=training_form, values_form=values_form)


@main.route('/export')
@main.route('/export/<string:team>')
@login_required
def export(team=''):
    if current_user.is_hr:
        if team == 'team':
            pdgs = []
            pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

            pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

            all_pdgs = list(chain(*pdgs))
        else:

            all_pdgs = PDG.query.filter_by(approved=True).all()
    elif current_user.role_id == 2:
        pdgs = []
        pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

        pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

        all_pdgs = list(chain(*pdgs))

    else:
        all_pdgs = PDG.query.filter_by(user_id=current_user.id).all()

    response = Response()
    response.status_code = 200

    # Create an in-memory output file for the new workbook.
    output = BytesIO()

    # Create workbook

    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet('PDGExport')

    worksheet.set_column("A:A", 30)  # Set the width of the first column
    worksheet.set_column("B:B", 20)  # Set the width of the second column
    worksheet.set_column("C:C", 20)  # Set the width of the third column
    worksheet.set_column("D:D", 50)  # Set the width of the sixth column
    worksheet.set_column("E:E", 50)  # Set the width of the sixth column
    worksheet.set_column("F:F", 30)  # Set the width of the sixth column

    header_format = workbook.add_format({
        'bold': True,
        'valign': 'top',
        'fg_color': '#D3D3D3',
        'border': 1})

    headers = ('Employee Name', 'Supervisor', 'Current Position', 'Review Period', 'Overall Feedback from Employee',
               'Overall Feedback from Supervisor', 'Overall Rating')
    for i, header in enumerate(headers):
        worksheet.write(0, i, header, header_format)

    # Write some test data.
    row = 1
    for pdg in all_pdgs:
        user = User.query.filter_by(id=pdg.user_id).first()
        supervisor = User.query.filter_by(email=user.supervisor).first()

        worksheet.write(row, 0, user.username)
        worksheet.write(row, 1, supervisor.username)
        worksheet.write(row, 2, user.position)
        worksheet.write(row, 3, pdg.review_year)
        worksheet.write(row, 4, pdg.employee_feedback)
        worksheet.write(row, 5, pdg.supervisor_feedback)
        worksheet.write(row, 6, pdg.rating)

        row += 1

    # Close the workbook before streaming the data.
    workbook.close()

    # Rewind the buffer.
    output.seek(0)

    # Add output to response
    response.data = output.read()

    # Set filname and mimetype
    file_name = f'PDG_Report_{datetime.now()}.xlsx'
    mimetype_tuple = mimetypes.guess_type(file_name)

    # HTTP headers for forcing file download
    response_headers = Headers({
        'Pragma': "public",  # required,
        'Expires': '0',
        'Cache-Control': 'must-revalidate, post-check=0, pre-check=0',
        'Cache-Control': 'private',  # required for certain browsers,
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': 'attachment; filename=\"%s\";' % file_name,
        'Content-Transfer-Encoding': 'binary',
        'Content-Length': len(response.data)
    })

    if not mimetype_tuple[1] is None:
        response.update({
            'Content-Encoding': mimetype_tuple[1]
        })

    # Add headers
    response.headers = response_headers

    # jquery.fileDownload.js requirements
    response.set_cookie('fileDownload', 'true', path='/')

    # Return the response
    return response


@main.route("/print/<pdg_id>")
@login_required
def print_pdg(pdg_id):
    pdg = PDG.query.filter_by(id=pdg_id, user_id=current_user.id).first()

    if not pdg:
        if current_user.is_hr == True:
            pdg = PDG.query.filter_by(id=pdg_id).first()

        elif current_user.role_id == 2:
            pdg = check_pdgs_of_users_below_supervisor(current_user.email, pdg_id)

    if pdg:
        user = User.query.filter_by(id=pdg.user_id).first()

        value = Values.query.filter_by(pdg_id=pdg_id).first()
        supervisor = User.query.filter_by(email=current_user.supervisor).first()

        html = render_template('print/print.html', pdg=pdg, user=user, value=value, supervisor=supervisor)
        return render_pdf(HTML(string=html, base_url=request.base_url))

    return 'None'


# @main.route("/import")
# @login_required
# def import_pdg():
#     date_pattern = r'([0-9]{2}\/[0-9]{2}\/[0-9]{4})'
#     data = pd.read_excel(Config.FILES + 'PDG_Next.xlsx')
#     data = data.replace(np.nan, '', regex=True)
#     # index_date = data.columns.get_loc('Date')
#
#     # index_employee = data.columns.get_loc('Employee')
#     employees = User.query.all()
#
#     data['Email'] = ''
#
#     for index, row in data.iterrows():
#         # print(row['Date'])
#         for e in employees:
#             if row['Employee'] == e.username:
#                 data['Email'] = e.name
#
#                 supervisor = User.query.filter_by(email=e.supervisor).first()
#                 # date = datetime.strptime(row['Date'], '%Y/%m/%Y').date()
#                 date = datetime.strptime(str(row['Date']), '%Y-%m-%d %H:%M:%S').date()
#                 # print(date)
#
#                 pdg = PDG.query.filter_by(user_id=e.id).first()
#                 if not pdg:
#                     pdg = PDG(
#                         user_id=e.id,
#                         supervisor_id=supervisor.id,
#                         review_year=2021
#
#                     )
#                     # print(pdg.supervisor_id)
#                     db.session.add(pdg)
#                     db.session.commit()
#
#                 objective = Objective(
#                     objective=row['Objective'],
#                     measure_of_success=row['Measures'],
#                     timeline=row['Timeline'],
#                     date_set=date,
#                     pdg_id=pdg.id,
#
#                 )
#                 # print(objective.date_set)
#                 # print(pdg)
#                 db.session.add(objective)
#                 # db.session.commit()
#
#     return redirect(url_for('main.pdgs'))


@main.route('/pdg-status')
def pdg_status():
    # print(current_user.email)

    users = []
    users.append(User.query.filter_by(id=current_user.id).all())
    users.append(User.query.filter_by(supervisor=current_user.email).all())

    users = get_users_below_supervisor(current_user.email, users)
    # print(users)
    all_users = list(chain(*users))

    pdgs = []
    pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

    pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)
    # print(pdgs)

    all_pdgs = list(chain(*pdgs))

    return render_template('pdg/pdg-status.html', users=all_users, pdgs=all_pdgs)


@main.route('/logs')
def logs():
    logs = Log.query.all()

    return render_template('logs.html', logs=logs)
