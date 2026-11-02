from app import database_io as db
import os
import pyrebase
import json
#import babel
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from app import app


if not os.environ.get('FLASK_SECRET_KEY'):
    raise RuntimeError('FLASK_SECRET_KEY must be set at runtime; see .env.example.')
app.config.update(
    SECRET_KEY=os.environ['FLASK_SECRET_KEY'],
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=os.getenv('SESSION_COOKIE_SECURE', '').lower() in {'1', 'true', 'yes'},
)

def _load_firebase_web_config():
    """Load Firebase's web configuration without storing it in source control."""
    raw = os.getenv('FIREBASE_WEB_CONFIG_JSON')
    path = os.getenv('FIREBASE_WEB_CONFIG_PATH')
    if raw:
        return json.loads(raw)
    if path:
        with open(path, encoding='utf-8') as config_file:
            return json.load(config_file)
    raise RuntimeError(
        'Firebase web configuration is not configured. Set FIREBASE_WEB_CONFIG_JSON '
        'or FIREBASE_WEB_CONFIG_PATH; see secrets/firebase-web-config.example.json.'
    )


firebase = pyrebase.initialize_app(_load_firebase_web_config())

auth = firebase.auth()


def check_token(f):
    @wraps(f)
    def wrap(*args,**kwargs):
        if 'user_id' not in session:
            return redirect('/')
        return f(*args, **kwargs)
    return wrap


@app.after_request
def add_header(response):
    response.cache_control.no_cache = True
    return response


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        email = request.form['name']
        password = request.form['pass']
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            # Keep only a harmless user identifier in the signed session cookie.
            # Firebase tokens are never sent back to the browser.
            session['user_id'] = user['localId']
            flash('You were successfully logged in')
            return redirect('/tip_create')
        except:
            flash('Please check your credentials')
            return render_template('login.html')
    return render_template('login.html', title='Login')


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['name']
        auth.send_password_reset_email(email)
        flash('Password reset email sent')
        return redirect('/')
    return render_template('reset.html', title='Reset Password')


@app.route('/logout')
def logout():
    # Clear session stored data
    session.clear()
    # Redirect user to login endpoint
    return redirect('/')


@app.template_filter('formatdatetime')
def format_datetime(value, format="%d %b %Y %I:%M %p"):
    """Format a date time to (Default): d Mon YYYY HH:MM P"""
    if value is None:
        return ""
    try:
        return datetime.strptime(value, '%Y-%m-%d').strftime('%-m/%-d/%Y')
    except:
        return value


@app.route('/teammates', methods=['GET', 'POST'])
@check_token
def provider_page():
    if request.method == 'POST':
        new_provider = request.form.to_dict()
        provider_doc = db.provider_create(new_provider)
    providers = db.providers_read_all('all')
    return render_template('providers.html', providers=providers, title='Providers')


@app.route('/provider_delete/<id>', methods=['POST'])
@check_token
def provider_delete(id):
    db.provider_delete(id)
    return redirect(url_for('provider_page'))


@app.route('/provider_edit/<id>', methods=['GET'])
@check_token
def provider_edit(id):
    provider = db.provider_read(id)
    return render_template('provider_edit.html', provider=provider, title='Provider Edit')


@app.route('/pay_periods', methods=['GET', 'POST'])
@check_token
def payperiods_page():
    if request.method == 'POST':
        new_pay_period = request.form.to_dict()
        pay_period_doc = db.payroll_period_create(new_pay_period)
    payroll_docs = db.payroll_period_read_all()
    return render_template('pay_periods.html', title='Pay Periods', periods=payroll_docs)


@app.route('/pay_period_delete/<id>', methods=['POST'])
@check_token
def pay_period_delete(id):
    if db.client_tips_by_pay_period_read(id):
        flash('Tips associated with pay period, cannot delete')
    else:
        db.payroll_period_delete(id)
    return redirect(url_for('payperiods_page'))


def summarize_tips(tips_data):
    summary = {'providers' : {}, 'visit_dates': {}, 'tip_total': 0.0, 'provider_tip_total': 0.0}
    for tip_id, tip_data in tips_data.items():
        #Create provider list with tip portions
        for provider in tip_data['providers']:
            if provider['provider_id'] in summary['providers']:
                summary['providers'][provider['provider_id']]['tips'].append(provider['tipportion'])
            else:
                summary['providers'][provider['provider_id']] = {'tips':[provider['tipportion']]}
            #Sum provider pieces of tip total
            summary['provider_tip_total'] = summary['provider_tip_total'] + float(provider['tipportion'])

        visit_date = tip_data.get('visit_date', 'No Visit Date')
        if visit_date in summary['visit_dates']:
            summary['visit_dates'][visit_date]['tips'].append(float(tip_data['tip_amount']))
        else:
            summary['visit_dates'][visit_date] = {'tips':[float(tip_data['tip_amount'])]}
        #Sum tips
        summary['tip_total'] = summary['tip_total'] + float(tip_data['tip_amount'])
    return summary


def attach_display_name(needs_names, names):
    for provider, data in needs_names.items():
        data['display_name'] = names[provider]['display_name']


@app.route('/payroll', methods=['GET', 'POST'])
@check_token
def payroll_summary_page():
    payroll_docs = db.payroll_period_read_all()
    if request.method == 'GET':
        # First Pay Period in the list
        pay_period_end = list(payroll_docs.keys())[0]
    elif request.method == 'POST':
        # Display the pay period just selected
        pay_period_end = request.form['pay_period_end']
    name_list = db.providers_read_all('all')
    tips = db.client_tips_by_pay_period_read(pay_period_end)
    summary = summarize_tips(tips)

    #Attach display names
    for tip_id, tip_data in tips.items():
        for provider in tip_data['providers']:
            provider['display_name'] = name_list[provider['provider_id']]['display_name']
    for provider, data in summary['providers'].items():
        data['display_name'] = name_list[provider]['display_name']

    return render_template(
        'payroll.html',
        title='Payroll Summary',
        summary=summary,
        payroll_periods=payroll_docs,
        tips=tips,
        pay_period_end=pay_period_end
    )


@app.route('/tips/<doc_id>')
@check_token
def tips_page(doc_id):
    single_tip = db.client_tip_read(doc_id)
    return render_template('tipdisplay.html', tip = single_tip)


def parse_new_tip(providers, unparsed_data):
    parsed_data = {key:unparsed_data[key] for key in ['payroll_end', 'client', 'tipamount', 'visit_date']}
    parsed_data['providers'] = []
    for provider in providers:
        provider_dict = {'provider_id':provider}
        for key, value in unparsed_data.items():
            split_key = key.split('_')
            if split_key[0] == provider:
                provider_dict[split_key[1]] = float(value)
        parsed_data['providers'].append(provider_dict)
    return parsed_data


@app.route('/tip_create', methods=['GET', 'POST'])
@check_token
def tip_create():
    tip_doc = None
    jobs_list = {'AA': 90, 'CO15': 15, 'HC': 15}
    if request.method == 'POST':
        providers = request.form.getlist('provider_id')
        tip_data = request.form.to_dict()
        tip_doc = db.client_tip_create(parse_new_tip(providers, tip_data))

    payroll_docs = db.payroll_period_read_all()
    providers = db.providers_read_all('active')
    single_tip = None
    if tip_doc:
        single_tip = db.client_tip_read(tip_doc)
    return render_template(
        'tipcreate.html',
        title='Tip Create',
        tip = single_tip,
        payroll_periods = payroll_docs,
        providers = providers,
        jobs_list = jobs_list
    )


@app.route('/tip_delete/<id>', methods=['POST'])
@check_token
def tip_delete(id):
    db.client_tip_delete(id)
    return redirect(url_for('payroll_summary_page'))


if __name__ == '__main__':
    app.debug = os.getenv('FLASK_DEBUG', '').lower() in {'1', 'true', 'yes'}
    app.run()
