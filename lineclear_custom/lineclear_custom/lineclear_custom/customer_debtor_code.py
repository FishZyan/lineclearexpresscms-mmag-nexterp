# your_app/api.py

import frappe

def check_before_submit(doc, method):
    if not (doc.customer_name):
        doc.customer_name = doc.customer_name

def sales_invoice_before_submit(doc, method):
    if not (doc.customer_name):
        doc.customer_name = doc.customer_name