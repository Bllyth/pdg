from datetime import datetime
from io import BytesIO
import mimetypes
from itertools import chain

import xlsxwriter
from O365 import Account
from flask import render_template, url_for, flash, redirect, request, send_file, Response
from flask_dance.contrib.azure import azure
from flask_login import login_required, current_user
import pandas as pd
from flask_sqlalchemy import Pagination
from flask_weasyprint import render_pdf
from weasyprint import HTML
from oauthlib.oauth2 import TokenExpiredError
from sqlalchemy import or_
from werkzeug.datastructures import Headers

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
    page = request.args.get('page', 1, type=int)
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
    page = request.args.get('page', 1, type=int)
    users = User.query.filter_by(supervisor=supervisor_email).all()
    for user in users:
        # get pdg matching user.id and pdg_id
        pdg = PDG.query.filter_by(user_id=user.id, status=True).all()

        if pdg:
            pdgs.append(pdg)
        pdgs = get_pdgs_below_supervisor(user.email, pdgs)
    return pdgs


# "select u.username as 'Employee Name', u.position as 'Current Position', review_year as 'Review Period', employee_feedback as 'Overall Feedback from Employee', supervisor_feedback as 'Overall Feedback from Supervisor', rating as 'Overall Rating' from dbo.pdg inner join users s on s.id = pdg.supervisor_id inner join users u on u.id = pdg.user_id"


# def get_pdgs_for_export(supervisor_email, pdgs):
#     # users = Get all users with supervisor_id as the supervisor
#     users = User.query.filter_by(supervisor=supervisor_email).all()
#     for user in users:
#         # get pdg matching user.id and pdg_id
#         pdg = f"select u.username as 'Employee Name', u.position as 'Current Position', " \
#               "review_year as 'Review Period', employee_feedback  as 'Overall Feedback from Employee', " \
#               "supervisor_feedback as 'Overall Feedback from Supervisor', rating as 'Overall Rating' " \
#               "from dbo.pdg inner join users s on s.id = pdg.supervisor_id inner join users u on u.id = pdg.user_id" \
#               " WHERE dbo.pdg.user_id={user.user.id}"
#
#         # pdg = PDG.query.filter_by(user_id=user.id, status=True).all()
#
#         if pdg:
#             pdgs.append(pdg)
#         pdgs = get_pdgs_below_supervisor(user.email, pdgs)
#     return pdgs


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
    # print(current_user.supervisor)
    page = request.args.get('page', 1, type=int)
    if current_user.role_id == 3:
        all_pdgs = PDG.query.filter_by(status=True).order_by(PDG.id.desc()).paginate(page, Config.PDGS_PER_PAGE, False)
    elif current_user.role_id == 2:
        pdgs = []
        pdgs.append(PDG.query.filter_by(user_id=current_user.id).all())

        pdgs = get_pdgs_below_supervisor(current_user.email, pdgs)

        pdgs = list(chain(*pdgs))

        print(pdgs)

        start = (page - 1) * 20
        end = start + 20
        # page 1 is [0:20], page 2 is [20:41]
        items = pdgs[start:end]

        all_pdgs = Pagination(None, page, Config.PDGS_PER_PAGE, len(pdgs), pdgs)
        print(all_pdgs)
        for p in all_pdgs.iter_pages():
            print(p)

    else:
        all_pdgs = PDG.query.filter_by(user_id=current_user.id).order_by(PDG.id.desc()).paginate(page, Config.PDGS_PER_PAGE, False)

    next_url = url_for('main.pdgs', page=all_pdgs.next_num) \
        if all_pdgs.has_next else None

    print(next_url)
    prev_url = url_for('main.pdgs', page=all_pdgs.prev_num) \
        if all_pdgs.has_prev else None
    return render_template('pdg/all_pdgs.html', all_pdg=all_pdgs, next_url=next_url,
                           prev_url=prev_url)


@main.route('/new-pdg', methods=['GET', 'POST'])
@login_required
def new_pdg():
    objective_form = ObjectiveForm(prefix='objs-_-')
    values_form = ValuesForm()
    future_form = NextYearObjectiveForm(prefix='futures-_-')
    training_form = TrainingForm(prefix='trainings-_-')

    supervisor = User.query.filter_by(email=current_user.supervisor).first()
    # print(supervisor.username)
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
            # db.session.commit()

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

    # print(current_user.role_id)

    pdg = PDG.query.filter_by(id=pdg_id, user_id=current_user.id).first()

    if not pdg:
        if current_user.role_id == 3:
            pdg = PDG.query.filter_by(id=pdg_id, approved=True).first()

        elif current_user.role_id == 2:
            pdg = check_users_below_supervisor(current_user.email, pdg_id)

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
                pdg.supervisor_feedback = form.supervisor_feedback.data
                pdg.rating = form.rating.data
                # pdg.date_of_review = form.date_of_review.data
                # pdg.review_year = form.review_year.data



                    # print('Objective', form.objs[0].supervisor_evaluation.data)

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
                    return redirect(url_for('main.pdgs'))

                if request.form['btn'] == 'submit':
                    pdg.status = True
                    db.session.commit()

                    flash('Pdg submitted successfully', 'success')

                    return redirect(url_for('main.pdgs'))

                for objective in pdg.objectives:
                    objective.supervisor_evaluation = request.form[objective.id]

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
        values_form.client_focus.data = value.client_focus
        values_form.boundless.data = value.boundless
        values_form.collaborate.data = value.collaborate
        values_form.integrity.data = value.integrity
        values_form.personal_excellence.data = value.personal_excellence

    if form.validate():

        value.client_focus = values_form.client_focus.data
        value.boundless = values_form.boundless.data
        value.collaborate = values_form.collaborate.data
        value.integrity = values_form.integrity.data
        value.personal_excellence = values_form.personal_excellence.data,
        pdg.employee_feedback = form.employee_feedback.data,
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
@login_required
def export():
    if current_user.role_id == 3:
        all_pdgs = PDG.query.filter_by(status=True).all()
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

    headers = ('Employee Name', 'Current Position', 'Review Period', 'Overall Feedback from Employee',
               'Overall Feedback from Supervisor', 'Overall Rating')
    for i, header in enumerate(headers):
        worksheet.write(0, i, header, header_format)

    # Write some test data.
    row = 1
    for pdg in all_pdgs:
        user = User.query.filter_by(id=pdg.user_id).first()

        worksheet.write(row, 0, user.username)
        worksheet.write(row, 1, user.position)
        worksheet.write(row, 2, pdg.review_year)
        worksheet.write(row, 3, pdg.employee_feedback)
        worksheet.write(row, 4, pdg.supervisor_feedback)
        worksheet.write(row, 5, pdg.rating)

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
    form = MainForm()
    objective_form = ObjectiveForm()
    pdg_edit = PDGEditForm()
    pdg = PDG.query.filter_by(id=pdg_id, user_id=current_user.id).first()

    # pdg = PDG.query.filter_by(id=pdg_id).first()

    if not pdg:
        if current_user.role_id == 3:
            pdg = PDG.query.filter_by(id=pdg_id).first()

        elif current_user.role_id == 2:
            pdg = check_users_below_supervisor(current_user.email, pdg_id)

    # print(pdg)
    if pdg:
        user = User.query.filter_by(id=pdg.user_id).first()

        # print(pdg.status)

        value = Values.query.filter_by(id=pdg_id).first()
        supervisor = User.query.filter_by(email=current_user.supervisor).first()

        html = render_template('print/print.html', pdg=pdg, user=user, value=value, supervisor=supervisor)
        return render_pdf(HTML(string=html, base_url='.'))

    return 'None'
