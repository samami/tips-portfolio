from distutils.util import strtobool
import json
import os

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from flask import flash

def _load_service_account():
    """Load a fresh Firebase credential supplied only at runtime."""
    raw = os.getenv('FIREBASE_SERVICE_ACCOUNT_JSON')
    path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    if raw:
        return json.loads(raw)
    if path:
        with open(path, encoding='utf-8') as credential_file:
            return json.load(credential_file)
    raise RuntimeError(
        'Firebase Admin credentials are not configured. Set FIREBASE_SERVICE_ACCOUNT_JSON '
        'or FIREBASE_SERVICE_ACCOUNT_PATH; see secrets/firebase-service-account.example.json.'
    )


cred = credentials.Certificate(_load_service_account())
firebase_admin.initialize_app(cred)

db = firestore.client()


def payroll_period_create(data):
    """Writes a payroll period document to the payroll_periods collection

    The document name is the payroll period ending date in ISO form
    """
    payroll_period_ending = data['payroll_period_ending']
    start_date = data['start_date']
    end_date = data['end_date']

    payroll_period_data = ({
        'payroll_period_ending': payroll_period_ending,
        'start_date': start_date,
        'end_date': end_date,
        'date_entered': firestore.SERVER_TIMESTAMP,
    })

    # Payroll period ending is document name because then you can't have duplicate payroll periods
    doc_ref = db.collection('payroll_periods').document(payroll_period_ending)
    doc_ref.set(payroll_period_data)
    return doc_ref.id


def payroll_period_delete(document_id):
    """Deletes a payroll period document from the payroll_periods collection"""
    db.collection('payroll_periods').document(document_id).delete()


def payroll_period_read(document_id):
    """Reads a payroll period document from the payroll_periods collection"""
    doc_ref = db.collection('payroll_periods').document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        flash('No such document!')
        return None


def payroll_period_read_all():
    users_ref = db.collection('payroll_periods').order_by('payroll_period_ending', direction=firestore.Query.DESCENDING)
    docs = users_ref.stream()
    docs_dict = {doc.id: doc.to_dict() for doc in docs}
    return docs_dict


def provider_create(data):
    """Creates a provider document in the providers collection

    A provider is an employee
    """
    provider_id = data['provider_id']
    first_name = data['first_name']
    last_name = data['last_name']
    display_name = data['display_name']
    is_active = bool(strtobool(data['is_active']))
    if 'is_update' in data.keys():
        is_update = bool(strtobool(data['is_update']))
    else:
        is_update = False

    provider_data = ({
        'provider_id': provider_id,
        'first_name': first_name,
        'last_name': last_name,
        'display_name': display_name,
        'is_active': is_active,
        'date_entered': firestore.SERVER_TIMESTAMP,
    })

    doc_ref = db.collection('providers').document(provider_id)
    doc = doc_ref.get()
    if (not doc.exists or is_update):
        doc_ref.set(provider_data)
    else:
        flash('ID already exists')
    return doc_ref.id


def provider_delete(document_id):
    """Deletes a provider document from the providers collection"""
    db.collection('providers').document(document_id).delete()


def provider_read(document_id):
    """Reads a provider document from the providers collection"""
    doc_ref = db.collection('providers').document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        flash('No such document!')
        return None


def providers_read_all(provider_status):
    provider_ref = db.collection('providers')
    if provider_status == 'active':
        query = provider_ref.where('is_active', '==', True).order_by('display_name')
    elif provider_status == 'inactive':
        query = provider_ref.where('is_active', '==', False).order_by('last_name')
    else:
        query = provider_ref.order_by('is_active', direction=firestore.Query.DESCENDING).order_by('last_name')
    docs = query.stream()
    docs_dict = {doc.id: doc.to_dict() for doc in docs}
    return docs_dict


def client_tip_create(data):
    payroll_period = data['payroll_end']
    client_name = data['client']
    tip_amount = data['tipamount']
    provider_data = data['providers']
    visit_date = data['visit_date']

    tip_data = ({
        'payroll_period': payroll_period,
        'date_entered': firestore.SERVER_TIMESTAMP,
        'client': client_name,
        'tip_amount': tip_amount,
        'providers': provider_data,
        'visit_date': visit_date
    })
    doc_ref = db.collection('client_tips').document()
    doc_ref.set(tip_data)
    return doc_ref.id


def client_tip_delete(document_id):
    """Deletes a client tip document from the client_tips collection"""
    db.collection('client_tips').document(document_id).delete()


def client_tip_read(document_id):
    """Reads a client tip document from the client_tips collection"""
    doc_ref = db.collection('client_tips').document(document_id)
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    else:
        flash(f'No such document! {document_id}')
        return None


def client_tips_by_pay_period_read(pay_period_id):
    """Reads the client tip documents for a specific pay period"""
    pay_period_id = pay_period_id
    # Create a reference to the client tips collection
    tip_ref = db.collection('client_tips')

    # Create a query against the collection
    query_ref = tip_ref.where('payroll_period', '==', pay_period_id)
    docs = query_ref.stream()
    docs_dict = {doc.id: doc.to_dict() for doc in docs}
    return docs_dict


def read_from_collection(collection_name):
    users_ref = db.collection(collection_name)
    docs = users_ref.stream()

    output = ''
    for doc in docs:
        output = output + str(doc.to_dict()) + "\n"

    return output
