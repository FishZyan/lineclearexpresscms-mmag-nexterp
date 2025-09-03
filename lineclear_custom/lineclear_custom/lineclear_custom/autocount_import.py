import sys
import requests
import json
from datetime import datetime, timedelta
import csv
import frappe
import os
import time
from collections import defaultdict
# import psycopg2
# import pyodbc
# import pymssql

# user = "nexterp"
# password = ""

# user = "sa"
# password = ""
# database = "AED_LINE"
# server = "127.0.0.1"

company = "Line Clear Express Sdn Bhd"
currency = "MYR"
headers = {
        "Authorization": "Token :",
        "Content-Type": "application/json"
    }
"""bench console
    from lineclear_custom.lineclear_custom.autocount_import import import_data
    import_data("Sales Invoice", filename)
"""
#0  1                2           3                 4                 5           6               7          8             9       10        11
#ID	Posting Date	Debtor Code	 Reference No	Payment Due Date	Subtotal    Income Account	Lhdn Tax	Description	  Agent   Tax Rate   Project No
def import_sales_invoice(rows, writer):
    erp_url = "http://localhost/api/resource/Sales%20Invoice"
    previous_id = ""
    all_item = []
    tax = []
    data= {}
    skip_invoice = ""
    for sales_invoice in rows:
        if(sales_invoice[0] == skip_invoice):
            continue
        if(sales_invoice[0] == previous_id): #if multiple references to the same sales invoice
            if(sales_invoice[6].startswith(("GST", "SST"))):
                account_name = frappe.get_doc("Account", {"account_number": sales_invoice[6]})
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(sales_invoice[5]),
                    "account_head": account_name.name,
                    "description": sales_invoice[8] or 'No Description'
                }
                tax.append(tax_item)
            elif sales_invoice[6] == "905-0007":
                data["disable_rounded_total"] = 0
            else:
                account_name = frappe.get_doc("Account", {"account_number": sales_invoice[6]})
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": sales_invoice[10]})
                except:
                    tax_code = None
                if(tax_code):
                    item = {
                        "item_code": "Courier Service",
                        "qty": 1,
                        "description": sales_invoice[8] or 'No Description',
                        "rate": float(sales_invoice[5]),
                        "income_account": account_name.name,
                        "custom_tax_amount": sales_invoice[12],
                        "custom_tax_code" : tax_code.name,
                        "custom_lhdn_tax_type": "02"
                    }
                else:
                    item = {
                        "item_code": "Courier Service",
                        "qty": 1,
                        "description": sales_invoice[8] or 'No Description',
                        "rate": float(sales_invoice[5]),
                        "income_account": account_name.name,
                        "custom_tax_amount": sales_invoice[12],
                        "custom_lhdn_tax_type": "02"
                    }
                all_item.append(item)
            continue
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != sales_invoice[0]):
                        data["items"] = all_item
                        data["taxes"] = tax
                        if(data["items"] == []):
                            data["items"] = [{
                                "item_code": "Courier Service",
                                "qty": 1,
                                "description": "No Item",
                                "rate": 0,
                                "income_account": "501-1000 - INCOME - TRANSPORTATION - LCESB"
                            }]
                        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
                        if response.status_code == 200:
                            writer.writerow(["Imported", previous_id])
                        else:
                            writer.writerow(["Error", previous_id, response.text])

            data = {}
            tax = []
            all_item = []
            previous_id = sales_invoice[0]

            try:
                check = frappe.get_doc("Sales Invoice", sales_invoice[0])
            except:
                check = None
            if check:
                skip_invoice = sales_invoice[0]
                writer.writerow(["Existed",  sales_invoice[0]])
                continue
            
            customer = get_customer(sales_invoice[2])
            if not customer:
                writer.writerow(["Customer Not Found", sales_invoice[0]])
                skip_invoice = sales_invoice[0]
                continue

            if not sales_invoice[6]:
                writer.writerow(["Income Account Not Found", sales_invoice[0]])
                skip_invoice = sales_invoice[0]
                continue

            if(sales_invoice[6].startswith(("GST", "SST"))):
                account_name = frappe.get_doc("Account", {"account_number": sales_invoice[6]})
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(sales_invoice[5]),
                    "account_head": account_name.name,
                    "description": sales_invoice[8]
                }
                tax.append(tax_item)
            elif sales_invoice[6] == "905-0007":
                pass
            else:
                account_name = frappe.get_doc("Account", {"account_number": sales_invoice[6]})
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": sales_invoice[10]})
                except:
                    tax_code = None
                if(tax_code):
                    item = {
                        "item_code": "Courier Service",
                        "qty": 1,
                        "description": sales_invoice[8] or 'No Description',
                        "rate": float(sales_invoice[5]),
                        "income_account": account_name.name,
                        "custom_tax_amount": sales_invoice[12],
                        "custom_tax_code" : tax_code.name,
                        "custom_lhdn_tax_type": "02"
                    }
                else:
                    item = {
                        "item_code": "Courier Service",
                        "qty": 1,
                        "description": sales_invoice[8] or 'No Description',
                        "rate": float(sales_invoice[5]),
                        "income_account": account_name.name,
                        "custom_tax_amount": sales_invoice[12],
                        "custom_lhdn_tax_type": "02"
                    }
                all_item.append(item)

            if sales_invoice[11]:
                cost_center_item = frappe.get_doc("Cost Center", sales_invoice[11])
                if cost_center_item:
                    cost_center = cost_center_item.name
                else:
                    writer.writerow(["Cost Center Not Found", sales_invoice[0]])
                    skip_invoice = sales_invoice[0]
                    continue
            else:
                cost_center = ""
            
            
            data = {
                "name" : sales_invoice[0],
                "company" : company,
                "posting_date": datetime.strptime(sales_invoice[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "set_posting_time": 1,
                "currency": currency,
                "selling_price_list": "Standard Selling",
                "custom_debtor_code": sales_invoice[2],
                "reference_no" : sales_invoice[3],
                "customer": customer,
                "due_date": datetime.strptime(sales_invoice[4], "%d/%m/%Y").strftime("%Y-%m-%d") if sales_invoice[4] else (datetime.strptime(sales_invoice[1], "%d/%m/%Y").strftime("%Y-%m-%d") + timedelta(days=14).strftime("%Y-%m-%d")),
                "agent": sales_invoice[9],
                "custom_tax_rate": sales_invoice[10] or '',
                "docstatus": 1,
                "disable_rounded_total": 1,
                "cost_center": cost_center
            }
            if (sales_invoice[6] == "905-0007"):
                data["disable_rounded_total"] = 0
            continue

    #Submit last sales invoice
    if(len(data) != 0):
        data["items"] = all_item
        data["taxes"] = tax
        if(data["items"] == []):
            data["items"] = [{
                "item_code": "Courier Service",
                "qty": 1,
                "description": "No Item",
                "rate": 0,
                "income_account": "501-1000 - INCOME - TRANSPORTATION - LCESB"
            }]
        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            pass
        else:
            print(response.text)
            writer.writerow(["Error",  sales_invoice[0]], response.text)

def import_payment_entry(rows, writer):
    erp_url = "http://localhost/api/resource/Payment%20Entry"
    previous_id = ""
    all_item = []
    data= {}
    skip_invoice = ""
    for payment_entry in rows:
        if(payment_entry[0] == skip_invoice):
            continue
        if(payment_entry[0] == previous_id): #if multiple references to the same sales invoice
            if not payment_entry[5]:
                writer.writerow(["Income Account Not Found", payment_entry[0]])
                skip_invoice = payment_entry[0]
                continue

            if(payment_entry[6] == 0):
                writer.writerow(["Payment amount is 0", payment_entry[0]])
                skip_invoice = payment_entry[0]
                continue
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": payment_entry[5]})
                except:
                    writer.writerow(["Account Not Found", payment_entry[0]])
                    skip_invoice = payment_entry[0]
                    continue

                #Find reference
                try: #Check if sales invoice reference exists
                    if(payment_entry[9]):
                        if(frappe.db.exists("Sales Invoice", payment_entry[9])):
                            reference_type = "Sales Invoice"
                            reference_name = frappe.get_doc("Sales Invoice", payment_entry[9])
                        elif(frappe.db.exists("Journal Entry", payment_entry[9])):
                            reference_type = "Journal Entry"
                            reference_name = frappe.get_doc("Journal Entry", payment_entry[9])
                        else:
                            writer.writerow(["Reference Not Found", payment_entry[0]])
                            skip_invoice = payment_entry[0]
                            data ={}
                            continue
                except:
                    writer.writerow(["Reference Not Found", payment_entry[0]])
                    skip_invoice = payment_entry[0]
                    data ={}
                    continue

                reference_item = {
                    "reference_doctype": reference_type,
                    "reference_name": reference_name.name,
                    "allocated_amount": round(float(payment_entry[10]), 2)
                }
                all_item.append(reference_item)
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != payment_entry[0]):
                        data["references"] = all_item
                        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
                        if response.status_code == 200:
                            pass
                        else:
                            print(response.text)
                            writer.writerow(["Error",  previous_id])

            data = {}
            all_item = []
            previous_id = payment_entry[0]

            try:
                check = frappe.get_doc("Payment Entry", payment_entry[0])
            except:
                check = None
            if check:
                skip_invoice = payment_entry[0]
                writer.writerow(["Existed",  payment_entry[0]])
                continue
            
            customer = get_customer(payment_entry[2])
            if not customer:
                writer.writerow(["Customer Not Found", payment_entry[0]])
                skip_invoice = payment_entry[0]
                continue

            if not payment_entry[5]:
                writer.writerow(["Income Account Not Found", payment_entry[0]])
                skip_invoice = payment_entry[0]
                continue

            if(float(payment_entry[6]) == 0 or not payment_entry[6]):
                writer.writerow(["Payment amount is 0", payment_entry[0]])
                skip_invoice = payment_entry[0]
                continue
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": payment_entry[5]})
                except:
                    writer.writerow(["Account Not Found", payment_entry[0]])
                    skip_invoice = payment_entry[0]
                    continue

                #Find reference
                try: #Check if sales invoice reference exists
                    if(payment_entry[9]):
                        if(frappe.db.exists("Sales Invoice", payment_entry[9])):
                            reference_type = "Sales Invoice"
                            reference_name = frappe.get_doc("Sales Invoice", payment_entry[9])
                        elif(frappe.db.exists("Journal Entry", payment_entry[9])):
                            reference_type = "Journal Entry"
                            reference_name = frappe.get_doc("Journal Entry", payment_entry[9])
                        else:
                            writer.writerow(["Reference Not Found", payment_entry[0]])
                            skip_invoice = payment_entry[0]
                            data ={}
                            continue
                except:
                    writer.writerow(["Reference Not Found", payment_entry[0]])
                    skip_invoice = payment_entry[0]
                    data ={}
                    continue

                reference_item = {
                    "reference_doctype": reference_type,
                    "reference_name": reference_name.name,
                    "allocated_amount": round(float(payment_entry[10]), 2)
                }
                all_item.append(reference_item)

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            data = {
                "name" : payment_entry[0],
                "payment_type": "Receive",
                "company" : company,
                "party_type" : "Customer",
                "posting_date": datetime.strptime(payment_entry[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "debtor_code": payment_entry[2],
                "party": customer,
                "party_name": customer,
                "mode_of_payment": payment_entry[3] or None,
                "paid_from": debtor_account_name,
                "paid_to": account_name.name,
                "paid_from_account_currency": currency,
                "paid_to_account_currency": currency,
                "remark": payment_entry[7],
                "paid_amount": round(float(payment_entry[6]), 2),
                "received_amount": round(float(payment_entry[6]), 2),
                "reference_no": payment_entry[11] or "No Cheque Number",
                "reference_date": datetime.strptime(payment_entry[12], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "docstatus": 1,
                "cost_center": "Main - LCESB"
            }
            continue

    #Submit last sales invoice
    if(len(data) != 0):
        data["references"] = all_item
        print(data)
        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            pass
        else:
            print(payment_entry[0])
            print(response.text)
            writer.writerow(["Error",  payment_entry[0]])

def import_credit_note(rows, writer):
    #0   1          2           3           4       5       6               7            8              9                   10                     11             12               13
    #ID	 DocDate	DebtorCode	UserRemark	Agent	HomeDR	DebitAccount	Description	 ReferenceType	ReferenceInvoice 	ItemClassificationCode	LhdnTaxType	   CreatedUserId	TaxCode
    erp_url = "http://localhost/api/resource/Journal%20Entry"
    previous_id = ""
    all_item = []
    tax = []
    data= {}
    skip_invoice = ""
    for credit_note in rows:
        if(credit_note[0] == skip_invoice):
            continue
        if(credit_note[0] == previous_id): #if multiple references to the same sales invoice
            if(credit_note[9]):
                reference_name = None
                reference_type = None
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", credit_note[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", credit_note[9])
                    elif(frappe.db.exists("Journal Entry", credit_note[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", credit_note[9])
                    else:
                        reference_type = None
                        reference_name = None
                except:
                    writer.writerow(["Reference Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(credit_note[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": credit_note[6]})
                except:
                    writer.writerow(["Account Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(credit_note[5]),
                    "account_head": account_name.name,
                    "description": credit_note[7]
                }
                tax.append(tax_item)
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(credit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "user_remark": credit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(credit_note[5]), 2),
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(debtor_account)
                custom_total_tax_amount += round(float(credit_note[5]), 2)
                net_total += round(float(credit_note[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": credit_note[6]})
                except:
                    writer.writerow(["Account Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": credit_note[13]})
                except:
                    tax_code = None
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(credit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(credit_note[5]), 2),
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(debtor_account)
                net_total += round(float(credit_note[5]), 2)
            continue
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != credit_note[0]):
                        data["accounts"] = all_item
                        data["tax"] = tax
                        data["net_total"] = net_total
                        data["custom_total_tax_amount"] = custom_total_tax_amount
                        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
                        if response.status_code == 200:
                            pass
                        else:
                            print(data)
                            print(response.text)
                            writer.writerow(["Error", previous_id])

            data = {}
            tax = []
            all_item = []
            previous_id = credit_note[0]
            net_total = 0.00
            custom_total_tax_amount = 0.00
            reference_type = None
            reference_name = None
            try:
                check = frappe.get_doc("Journal Entry", credit_note[0])
            except:
                check = None
            if check:
                skip_invoice = credit_note[0]
                writer.writerow(["Existed",  credit_note[0]])
                continue
            
            customer = get_customer(credit_note[2])
            if not customer:
                writer.writerow(["Customer Not Found", credit_note[0]])
                skip_invoice = credit_note[0]
                continue

            if not credit_note[5]:
                writer.writerow(["Total Amount Not Found", credit_note[0]])
                skip_invoice = credit_note[0]
                continue

            #Find reference
            if(credit_note[9]):
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", credit_note[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", credit_note[9])
                    elif(frappe.db.exists("Journal Entry", credit_note[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", credit_note[9])
                    else:
                        reference_type = None
                        reference_name = None
                except:
                    writer.writerow(["Reference Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(credit_note[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": credit_note[6]})
                except:
                    writer.writerow(["Account Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(credit_note[5]),
                    "account_head": account_name.name,
                    "description": credit_note[7]
                }
                tax.append(tax_item)
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(credit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "user_remark": credit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(credit_note[5]), 2),
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(debtor_account)
                custom_total_tax_amount += round(float(credit_note[5]), 2)
                net_total += round(float(credit_note[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": credit_note[6]})
                except:
                    writer.writerow(["Account Not Found", credit_note[0]])
                    skip_invoice = credit_note[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": credit_note[13]})
                except:
                    tax_code = None
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(credit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": credit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(credit_note[5]), 2),
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": credit_note[9]
                }
                all_item.append(debtor_account)
                net_total += round(float(credit_note[5]), 2)

            data = {
                "name" : credit_note[0],
                "voucher_type": "Credit Note",
                "company" : company,
                "custom_created_by": "System",
                "posting_date": datetime.strptime(credit_note[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "currency": currency,
                "customer": customer,
                "debtor_code" : credit_note[2],
                "user_remark": credit_note[3],
                "agent": credit_note[4],
                # "custom_tax_rate": credit_note[16] or '',
                # "item_classification_code": credit_note[13],
                "item_classification_code": "004",
                # "lhdn_tax_type": credit_note[14],
                "lhdn_tax_type": "02",
                "custom_created_by": credit_note[12],
                "docstatus": 1
            }

    #Submit last Credit Note
    if(len(data) != 0):
        data["accounts"] = all_item
        data["tax"] = tax
        data["net_total"] = net_total
        data["custom_total_tax_amount"] = custom_total_tax_amount
        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            pass
        else:
            print(response.text)
            writer.writerow(["Error", previous_id])

def import_debit_note(rows, writer):
    #0   1          2           3           4       5       6               7            8              9                   10                     11             12               13
    #ID	 DocDate	DebtorCode	UserRemark	Agent	HomeDR	DebitAccount	Description	 ReferenceType	ReferenceInvoice 	ItemClassificationCode	LhdnTaxType	   CreatedUserId	TaxCode
    erp_url = "http://localhost/api/resource/Journal%20Entry"
    previous_id = ""
    all_item = []
    tax = []
    data= {}
    skip_invoice = ""
    for debit_note in rows:
        if(debit_note[0] == skip_invoice):
            continue
        if(debit_note[0] == previous_id): #if multiple references to the same sales invoice
            if(debit_note[9]):
                reference_name = None
                reference_type = None
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", debit_note[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", debit_note[9])
                    elif(frappe.db.exists("Journal Entry", debit_note[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", debit_note[9])
                    else:
                        writer.writerow(["Reference Not Found", debit_note[0]])
                        skip_invoice = debit_note[0]
                        continue
                except:
                    writer.writerow(["Reference Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(debit_note[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": debit_note[6]})
                except:
                    writer.writerow(["Account Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(debit_note[5]),
                    "account_head": account_name.name,
                    "description": debit_note[7]
                }
                tax.append(tax_item)
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(debit_note[5]), 2),
                    "reference_type": None,
                    "reference_name": None,
                    "user_remark": debit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(debit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "user_remark": debit_note[9]
                }
                all_item.append(debtor_account)
                custom_total_tax_amount += round(float(debit_note[5]), 2)
                net_total += round(float(debit_note[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": debit_note[6]})
                except:
                    writer.writerow(["Account Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": debit_note[13]})
                except:
                    tax_code = None
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(debit_note[5]), 2),
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": debit_note[9]
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(debit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": debit_note[9]
                }
                all_item.append(debtor_account)
                net_total += round(float(debit_note[5]), 2)
            continue
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != debit_note[0]):
                        data["accounts"] = all_item
                        data["tax"] = tax
                        data["net_total"] = net_total
                        data["custom_total_tax_amount"] = custom_total_tax_amount
                        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
                        if response.status_code == 200:
                            pass
                        else:
                            print(response.text)
                            writer.writerow(["Error", previous_id])

            data = {}
            tax = []
            all_item = []
            previous_id = debit_note[0]
            net_total = 0.00
            custom_total_tax_amount = 0.00
            reference_type = None
            reference_name = None
            try:
                check = frappe.get_doc("Journal Entry", debit_note[0])
            except:
                check = None
            if check:
                skip_invoice = debit_note[0]
                writer.writerow(["Existed",  debit_note[0]])
                continue
            
            customer = get_customer(debit_note[2])
            if not customer:
                writer.writerow(["Customer Not Found", debit_note[0]])
                skip_invoice = debit_note[0]
                continue

            if not debit_note[5]:
                writer.writerow(["Total Amount Not Found", debit_note[0]])
                skip_invoice = debit_note[0]
                continue

            #Find reference
            if(debit_note[9]):
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", debit_note[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", debit_note[9])
                    elif(frappe.db.exists("Journal Entry", debit_note[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", debit_note[9])
                except:
                    writer.writerow(["Reference Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(debit_note[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": debit_note[6]})
                except:
                    writer.writerow(["Account Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(debit_note[5]),
                    "account_head": account_name.name,
                    "description": debit_note[7]
                }
                tax.append(tax_item)
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(debit_note[5]), 2),
                    "reference_type": None,
                    "reference_name": None
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(debit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None
                }
                all_item.append(debtor_account)
                custom_total_tax_amount += round(float(debit_note[5]), 2)
                net_total += round(float(debit_note[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": debit_note[6]})
                except:
                    writer.writerow(["Account Not Found", debit_note[0]])
                    skip_invoice = debit_note[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": debit_note[13]})
                except:
                    tax_code = None
                account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(debit_note[5]), 2),
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None
                }
                all_item.append(account)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": debit_note[7] or "No Description",
                    "debit_in_account_currency": round(float(debit_note[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": reference_type if reference_type else None,
                    "reference_name": reference_name.name if reference_name else None,
                    "custom_tax_code" : tax_code.name if tax_code else None
                }
                all_item.append(debtor_account)
                net_total += round(float(debit_note[5]), 2)

            data = {
                "name" : debit_note[0],
                "voucher_type": "Debit Note",
                "company" : company,
                "custom_created_by": "System",
                "posting_date": datetime.strptime(debit_note[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "currency": currency,
                "customer": customer,
                "debtor_code" : debit_note[2],
                "user_remark": debit_note[3],
                "agent": debit_note[4],
                # "custom_tax_rate": credit_note[16] or '',
                # "item_classification_code": credit_note[13],
                "item_classification_code": "004",
                # "lhdn_tax_type": credit_note[14],
                "lhdn_tax_type": "02",
                "custom_created_by": debit_note[12],
                "docstatus": 1
            }
    
    #Submit last Credit Note
    if(len(data) != 0):
        data["accounts"] = all_item
        data["tax"] = tax
        data["net_total"] = net_total
        data["custom_total_tax_amount"] = custom_total_tax_amount
        print(data)
        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            pass
        else:
            print(response.text)
            writer.writerow(["Error", previous_id])


def import_journal_entry(rows, writer):
    #0   1          2           3           4       5       6               7            8              9                   10                      11             12               13           14
    #ID	 DocDate	DebtorCode	UserRemark	Agent	HomeDR	DebitAccount	Description	 ReferenceType	ReferenceInvoice 	ItemClassificationCode	LhdnTaxType	   CreatedUserId	TaxCode     SourceType
    erp_url = "http://localhost/api/resource/Journal%20Entry"
    previous_id = ""
    all_item = []
    tax = []
    data= {}
    skip_invoice = ""
    for journal_entry in rows:
        if(journal_entry[0] == skip_invoice):
            continue
        if(journal_entry[0] == previous_id): #if multiple references to the same sales invoice
            if(journal_entry[9]):
                reference_name = None
                reference_type = None
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", journal_entry[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                    elif(frappe.db.exists("Journal Entry", journal_entry[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                except:
                    writer.writerow(["Reference Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    data ={}
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(journal_entry[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                except:
                    writer.writerow(["Account Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(journal_entry[5]),
                    "account_head": account_name.name,
                    "description": journal_entry[7]
                }
                tax.append(tax_item)
                if(journal_entry[14] == "Debit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": None,
                        "reference_name": None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                elif(journal_entry [14] == "Credit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": None,
                        "reference_name": None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                custom_total_tax_amount += round(float(journal_entry[5]), 2)
                net_total += round(float(journal_entry[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                except:
                    writer.writerow(["Account Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": journal_entry[13]})
                except:
                    tax_code = None
                if(journal_entry[14] == "Debit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": None,
                        "reference_name": None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                elif(journal_entry[14] == "Credit Note"):
                    account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": journal_entry[7] or "No Description",
                    "debit_in_account_currency": round(float(journal_entry[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                net_total += round(float(journal_entry[5]), 2)
            continue
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != journal_entry[0]):
                        data["accounts"] = all_item
                        data["tax"] = tax
                        data["net_total"] = net_total
                        data["custom_total_tax_amount"] = custom_total_tax_amount
                        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
                        if response.status_code == 200:
                            pass
                        else:
                            print(response.text)
                            writer.writerow(["Error", previous_id])

            data = {}
            tax = []
            all_item = []
            previous_id = journal_entry[0]
            net_total = 0.00
            custom_total_tax_amount = 0.00
            reference_type = None
            reference_name = None
            try:
                check = frappe.get_doc("Journal Entry", journal_entry[0])
            except:
                check = None
            if check:
                skip_invoice = journal_entry[0]
                writer.writerow(["Existed",  journal_entry[0]])
                continue
            
            customer = get_customer(journal_entry[2])
            if not customer:
                writer.writerow(["Customer Not Found", journal_entry[0]])
                skip_invoice = journal_entry[0]
                continue

            if not journal_entry[5]:
                writer.writerow(["Total Amount Not Found", journal_entry[0]])
                skip_invoice = journal_entry[0]
                continue

            #Find reference
            if(journal_entry[9]):
                try: #Check if sales invoice reference exists
                    if(frappe.db.exists("Sales Invoice", journal_entry[9])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                    elif(frappe.db.exists("Journal Entry", journal_entry[9])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                except:
                    writer.writerow(["Reference Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    continue

            debtor = frappe.get_doc("Customer", customer)
            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                if(debtor.custom_debtor_type == "TD"):
                    debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                elif(debtor.custom_debtor_type == "NTD"):
                    debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            if(journal_entry[6].startswith(("GST", "SST"))):
                try:
                    account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                except:
                    writer.writerow(["Account Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    continue
                tax_item = {
                    "charge_type": "Actual",
                    "tax_amount": float(journal_entry[5]),
                    "account_head": account_name.name,
                    "description": journal_entry[7]
                }
                tax.append(tax_item)
                if(journal_entry[14] == "Debit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": None,
                        "reference_name": None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                elif(journal_entry [14] == "Credit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": None,
                        "reference_name": None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                custom_total_tax_amount += round(float(journal_entry[5]), 2)
                net_total += round(float(journal_entry[5]), 2)
            else:
                try:
                    account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                except:
                    writer.writerow(["Account Not Found", journal_entry[0]])
                    skip_invoice = journal_entry[0]
                    continue
                try:
                    tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": journal_entry[13]})
                except:
                    tax_code = None
                if(journal_entry[14] == "Debit Note"):
                    account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": None,
                        "reference_name": None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                elif(journal_entry[14] == "Credit Note"):
                    account = {
                    "account": account_name.name,
                    "party_type": None,
                    "party": None,
                    "custom_description": journal_entry[7] or "No Description",
                    "debit_in_account_currency": round(float(journal_entry[5]), 2),
                    "credit_in_account_currency": 0,
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : tax_code.name if tax_code else None,
                    "user_remark": journal_entry[9]
                    }
                    all_item.append(account)
                    debtor_account = {
                        "account": debtor_account_name,
                        "party_type": "Customer",
                        "party": customer,
                        "custom_description": journal_entry[7] or "No Description",
                        "debit_in_account_currency": 0,
                        "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        "reference_type": reference_type if reference_type else None,
                        "reference_name": reference_name.name if reference_name else None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                    }
                    all_item.append(debtor_account)
                net_total += round(float(journal_entry[5]), 2)

            data = {
                "name" : journal_entry[0],
                "voucher_type": journal_entry[14],
                "company" : company,
                "custom_created_by": "System",
                "posting_date": datetime.strptime(journal_entry[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                "currency": currency,
                "customer": customer,
                "debtor_code" : journal_entry[2],
                "user_remark": journal_entry[3],
                "agent": journal_entry[4],
                # "custom_tax_rate": credit_note[16] or '',
                # "item_classification_code": credit_note[13],
                "item_classification_code": "004",
                # "lhdn_tax_type": credit_note[14],
                "lhdn_tax_type": "02",
                "custom_created_by": journal_entry[12],
                "docstatus": 1
            }
    
    
    #Submit last Credit Note
    if(len(data) != 0):
        data["accounts"] = all_item
        data["tax"] = tax
        data["net_total"] = net_total
        data["custom_total_tax_amount"] = custom_total_tax_amount
        print(data)
        response = requests.post(erp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            pass
        else:
            print(response.text)
            writer.writerow(["Error", previous_id])

def all_import(rows, writer):
    #0   1          2           3           4       5       6               7            8              9                   10                      11             12               13           14
    #ID	 DocDate	DebtorCode	UserRemark	Agent	HomeDR	DebitAccount	Description	 ReferenceType	ReferenceInvoice 	ItemClassificationCode	LhdnTaxType	   CreatedUserId	TaxCode     SourceType
    JEerp_url = "http://localhost/api/resource/Journal%20Entry"
    PEerp_url = "http://localhost/api/resource/Payment%20Entry"
    previous_id = ""
    all_item = []
    tax = []
    data= {}
    skip_invoice = ""
    previous_type = ""
    payment_account = ""
    remaining_ammount = 0
    previous_customer = ""
    previous_description = ""
    net_total = 0
    for journal_entry in rows:
        if(journal_entry[0] == skip_invoice):
            continue
        if(journal_entry[0] == previous_id): #if multiple references to the same sales invoice
            if(journal_entry[14] == "Credit Note" or journal_entry[14] == "Debit Note"):
                if(journal_entry[9] and journal_entry[14] == "Debit Note"):
                    reference_name = None
                    reference_type = None
                    try: #Check if sales invoice reference exists
                        if(frappe.db.exists("Sales Invoice", journal_entry[9])):
                            reference_type = "Sales Invoice"
                            reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                            if reference_name.custom_debtor_code != journal_entry[2]:
                                writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                        elif(frappe.db.exists("Journal Entry", journal_entry[9])):
                            reference_type = "Journal Entry"
                            reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                            if reference_name.debtor_code != journal_entry[2]:
                                writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                        else:
                            writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                            skip_invoice = journal_entry[0]
                            data ={}
                            continue
                    except:
                        writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                        skip_invoice = journal_entry[0]
                        data ={}
                        continue

                debtor = frappe.get_doc("Customer", customer)
                debtor_account_name = None
                for account in debtor.accounts:
                    debtor_account_name = account.account
                    break
                if not debtor_account_name:
                    if(debtor.custom_debtor_type == "TD"):
                        debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                    elif(debtor.custom_debtor_type == "NTD"):
                        debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

                description = journal_entry[7]
                # if journal_entry[9]:
                #     description += " Reference :" + journal_entry[9]

                if(journal_entry[6].startswith(("GST", "SST"))):
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0]])
                        skip_invoice = journal_entry[0]
                        continue
                    tax_item = {
                        "charge_type": "Actual",
                        "tax_amount": float(journal_entry[5]),
                        "account_head": account_name.name,
                        "description": description or "No Description"
                    }
                    tax.append(tax_item)
                    if(journal_entry[14] == "Debit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": 0,
                            "credit_in_account_currency": round(float(journal_entry[5]), 2),
                            "reference_type": None,
                            "reference_name": None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        debtor_account = {
                            "account": debtor_account_name,
                            "party_type": "Customer",
                            "party": customer,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": reference_type if reference_type else None,
                            "reference_name": reference_name.name if reference_name else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(debtor_account)
                    elif(journal_entry [14] == "Credit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": None,
                            "reference_name": None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                    custom_total_tax_amount += round(float(journal_entry[5]), 2)
                    net_total += round(float(journal_entry[5]), 2)
                else:
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0]])
                        skip_invoice = journal_entry[0]
                        continue
                    try:
                        tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": journal_entry[13]})
                    except:
                        tax_code = None
                    if(journal_entry[14] == "Debit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": 0,
                            "credit_in_account_currency": round(float(journal_entry[5]), 2),
                            "reference_type": None,
                            "reference_name": None,
                            "custom_tax_code" : tax_code.name if tax_code else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        debtor_account = {
                            "account": debtor_account_name,
                            "party_type": "Customer",
                            "party": customer,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": reference_type if reference_type else None,
                            "reference_name": reference_name.name if reference_name else None,
                            "custom_tax_code" : tax_code.name if tax_code else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(debtor_account)
                    elif(journal_entry[14] == "Credit Note"):
                        account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": description or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": None,
                        "reference_name": None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                    net_total += round(float(journal_entry[5]), 2)
                continue
            elif (journal_entry[14] == "Payment Entry"):
                if not journal_entry[6]:
                    writer.writerow(["Income Account Not Found", journal_entry[0], "Payment Entry"])
                    skip_invoice = journal_entry[0]
                    continue
                
                if journal_entry[6] != payment_account:
                    writer.writerow(["Different Payment Account", journal_entry[0], "Payment Entry"])
                    skip_invoice = journal_entry[0]
                    continue

                if(journal_entry[5] == 0):
                    writer.writerow(["Payment amount is 0", journal_entry[0], "Payment Entry"])
                    skip_invoice = journal_entry[0]
                    continue
                else:
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0], "Payment Entry"])
                        skip_invoice = journal_entry[0]
                        continue

                    #Find reference
                    try: #Check if sales invoice reference exists
                        if(journal_entry[9]):
                            if(journal_entry[8] == "RI" and frappe.db.exists("Sales Invoice", journal_entry[9])):
                                reference_type = "Sales Invoice"
                                reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                                if reference_name.custom_debtor_code != journal_entry[2]:
                                    writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    data ={}
                                    continue
                            elif(journal_entry[8] == "RD" and frappe.db.exists("Journal Entry", journal_entry[9])):
                                reference_type = "Journal Entry"
                                reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                                if reference_name.debtor_code != journal_entry[2]:
                                    writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    data ={}
                                    continue
                            else:
                                writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                    except:
                        writer.writerow(["Unexpected Error", journal_entry[0], "Payment Entry"])
                        skip_invoice = journal_entry[0]
                        data ={}
                        continue
                    if(reference_type == "Journal Entry"):
                        # for item in all_item:
                        #     if item["reference_name"] == reference_name.name and item["reference_doctype"] == reference_type:
                        #         # Found, update the allocated_amount
                        #         item["allocated_amount"] += round(float(journal_entry[10]), 2)
                        #         continue
                        # else:
                        reference_item = {
                            "reference_doctype": reference_type,
                            "reference_name": reference_name.name,
                            "allocated_amount": round(float(journal_entry[10]), 2)
                        }
                        all_item.append(reference_item)
                    elif(reference_type == "Sales Invoice"):
                        # for item in all_item:
                        #     if item["reference_name"] == reference_name.name and item["reference_doctype"] == reference_type:
                        #         # Found, update the allocated_amount
                        #         amount = item["allocated_amount"] + round(float(journal_entry[10]), 2)
                        #         if(reference_name.outstanding_amount <= 0):
                        #             break
                        #         if(amount < float(reference_name.outstanding_amount)):
                        #             item["allocated_amount"] = amount
                        #         else:
                        #             item["allocated_amount"] = reference_name.outstanding_amount
                        #         break
                        # else:
                        if round(float(journal_entry[10]), 2) > float(reference_name.outstanding_amount):
                            writer.writerow(["Reference Amount larger than total amount", journal_entry[0], journal_entry[14]])
                            skip_invoice = journal_entry[0]
                            data ={}
                            continue
                        else:
                            reference_item = {
                                "reference_doctype": reference_type,
                                "reference_name": reference_name.name,
                                "allocated_amount": round(float(journal_entry[10]), 2)
                            }
                            all_item.append(reference_item)
                    continue
        else:
            if(len(data) != 0):
                if(previous_id != ""):
                    if(previous_id != journal_entry[0]):
                        if (previous_type == "Debit Note"):
                            data["accounts"] = all_item
                            data["tax"] = tax
                            data["net_total"] = net_total
                            data["custom_total_tax_amount"] = custom_total_tax_amount
                            response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
                            if response.status_code == 200:
                                pass
                            else:
                                print(response.text)
                                writer.writerow(["Error", previous_id, previous_type, response.text])
                        elif(previous_type == "Credit Note"):
                            if round(float(remaining_ammount),2) > round(float(net_total), 2):
                                writer.writerow(["Reference Amount larger than total amount", previous_id, previous_type])
                                skip_invoice = previous_id
                            elif round(float(remaining_ammount), 2) < round(float(net_total), 2):
                                customer = get_customer(previous_customer)
                                if not customer:
                                    writer.writerow(["Customer Not Found", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    continue
                                debtor = frappe.get_doc("Customer", customer)
                                debtor_account_name = None
                                for account in debtor.accounts:
                                    debtor_account_name = account.account
                                    break
                                if not debtor_account_name:
                                    if(debtor.custom_debtor_type == "TD"):
                                        debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                                    elif(debtor.custom_debtor_type == "NTD"):
                                        debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"
                                remain = round(float(net_total), 2) - round(float(remaining_ammount), 2)
                                debtor_account = {
                                    "account": debtor_account_name,
                                    "party_type": "Customer",
                                    "party": customer,
                                    "custom_description": previous_description or "No Description",
                                    "debit_in_account_currency": 0,
                                    "credit_in_account_currency": round(float(remain), 2),
                                    "reference_type": None,
                                    "reference_name": None,
                                    "custom_tax_code" : None,
                                    "user_remark": "No Reference"
                                }
                                all_item.append(debtor_account)
                                remaining_ammount += round(float(remain), 2)

                            if(round(float(remaining_ammount),2) == round(float(net_total), 2)):
                                data["accounts"] = all_item
                                data["tax"] = tax
                                data["net_total"] = net_total
                                data["custom_total_tax_amount"] = custom_total_tax_amount
                                response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
                                if response.status_code == 200:
                                    pass
                                else:
                                    print(response.text)
                                    writer.writerow(["Error", previous_id, previous_type, response.text])
                        elif(previous_type == "Payment Entry"):
                            data["references"] = all_item
                            response = requests.post(PEerp_url, headers=headers, data=json.dumps(data))
                            if response.status_code == 200:
                                writer.writerow(["Imported",  previous_id])
                            else:
                                print(json.loads(response.text))
                                writer.writerow(["Error",  previous_id, previous_type, response.text])

            data = {}
            tax = []
            all_item = []
            previous_id = journal_entry[0]
            net_total = 0.00
            custom_total_tax_amount = 0.00
            reference_type = None
            reference_name = None
            previous_type = journal_entry[14]
            remaining_ammount = 0
            previous_customer = journal_entry[2]
            previous_description = journal_entry[7]
            if (journal_entry[14] == "Credit Note" or journal_entry[14] == "Debit Note"):
                try:
                    check = frappe.get_doc("Journal Entry", journal_entry[0])
                except:
                    check = None
                if check:
                    skip_invoice = journal_entry[0]
                    writer.writerow(["Existed",  journal_entry[0], journal_entry[14]])
                    continue
                
                customer = get_customer(journal_entry[2])
                if not customer:
                    writer.writerow(["Customer Not Found", journal_entry[0], journal_entry[14]])
                    skip_invoice = journal_entry[0]
                    continue

                if not journal_entry[5]:
                    writer.writerow(["Total Amount Not Found", journal_entry[0], journal_entry[14]])
                    skip_invoice = journal_entry[0]
                    continue
                #Find reference
                if(journal_entry[9] and journal_entry[14] == "Debit Note"):
                    try: #Check if sales invoice reference exists
                        if(frappe.db.exists("Sales Invoice", journal_entry[9])):
                            reference_type = "Sales Invoice"
                            reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                            if reference_name.custom_debtor_code != journal_entry[2]:
                                writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                        elif(frappe.db.exists("Journal Entry", journal_entry[9])):
                            reference_type = "Journal Entry"
                            reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                            if reference_name.debtor_code != journal_entry[2]:
                                writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                    except:
                        writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                        skip_invoice = journal_entry[0]
                        continue

                debtor = frappe.get_doc("Customer", customer)
                debtor_account_name = None
                for account in debtor.accounts:
                    debtor_account_name = account.account
                    break
                if not debtor_account_name:
                    if(debtor.custom_debtor_type == "TD"):
                        debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                    elif(debtor.custom_debtor_type == "NTD"):
                        debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

                description = journal_entry[7]
                # if journal_entry[9]:
                #     description += " Reference :" + journal_entry[9]

                if(journal_entry[6].startswith(("GST", "SST"))):
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0], journal_entry[14]])
                        skip_invoice = journal_entry[0]
                        continue
                    tax_item = {
                        "charge_type": "Actual",
                        "tax_amount": float(journal_entry[5]),
                        "account_head": account_name.name,
                        "description": description or "No Description"
                    }
                    tax.append(tax_item)
                    if(journal_entry[14] == "Debit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": 0,
                            "credit_in_account_currency": round(float(journal_entry[5]), 2),
                            "reference_type": None,
                            "reference_name": None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        debtor_account = {
                            "account": debtor_account_name,
                            "party_type": "Customer",
                            "party": customer,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": reference_type if reference_type else None,
                            "reference_name": reference_name.name if reference_name else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(debtor_account)
                    elif(journal_entry [14] == "Credit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": None,
                            "reference_name": None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        # debtor_account = {
                        #     "account": debtor_account_name,
                        #     "party_type": "Customer",
                        #     "party": customer,
                        #     "custom_description": description or "No Description",
                        #     "debit_in_account_currency": 0,
                        #     "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        #     "reference_type": reference_type if reference_type else None,
                        #     "reference_name": reference_name.name if reference_name else None,
                        #     "user_remark": journal_entry[9]
                        # }
                        # all_item.append(debtor_account)
                    custom_total_tax_amount += round(float(journal_entry[5]), 2)
                    net_total += round(float(journal_entry[5]), 2)
                else:
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0], journal_entry[14]])
                        skip_invoice = journal_entry[0]
                        continue
                    try:
                        tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": journal_entry[13]})
                    except:
                        tax_code = None
                    if(journal_entry[14] == "Debit Note"):
                        account = {
                            "account": account_name.name,
                            "party_type": None,
                            "party": None,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": 0,
                            "credit_in_account_currency": round(float(journal_entry[5]), 2),
                            "reference_type": None,
                            "reference_name": None,
                            "custom_tax_code" : tax_code.name if tax_code else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        debtor_account = {
                            "account": debtor_account_name,
                            "party_type": "Customer",
                            "party": customer,
                            "custom_description": description or "No Description",
                            "debit_in_account_currency": round(float(journal_entry[5]), 2),
                            "credit_in_account_currency": 0,
                            "reference_type": reference_type if reference_type else None,
                            "reference_name": reference_name.name if reference_name else None,
                            "custom_tax_code" : tax_code.name if tax_code else None,
                            "user_remark": journal_entry[9]
                        }
                        all_item.append(debtor_account)
                    elif(journal_entry[14] == "Credit Note"):
                        account = {
                        "account": account_name.name,
                        "party_type": None,
                        "party": None,
                        "custom_description": description or "No Description",
                        "debit_in_account_currency": round(float(journal_entry[5]), 2),
                        "credit_in_account_currency": 0,
                        "reference_type": None,
                        "reference_name": None,
                        "custom_tax_code" : tax_code.name if tax_code else None,
                        "user_remark": journal_entry[9]
                        }
                        all_item.append(account)
                        # debtor_account = {
                        #     "account": debtor_account_name,
                        #     "party_type": "Customer",
                        #     "party": customer,
                        #     "custom_description": description or "No Description",
                        #     "debit_in_account_currency": 0,
                        #     "credit_in_account_currency": round(float(journal_entry[5]), 2),
                        #     "reference_type": reference_type if reference_type else None,
                        #     "reference_name": reference_name.name if reference_name else None,
                        #     "custom_tax_code" : tax_code.name if tax_code else None,
                        #     "user_remark": journal_entry[9]
                        # }
                        # all_item.append(debtor_account)
                    net_total += round(float(journal_entry[5]), 2)
                
                #Enter Credit Note Reference
                if(journal_entry[14] == "Credit Note"):
                    if(journal_entry[9]):
                        all_reference = journal_entry[9].split(";")
                        for item in all_reference:
                            reference, reference_amount = item.split(":")
                            try: #Check if sales invoice reference exists
                                if(frappe.db.exists("Sales Invoice", reference.strip())):
                                    reference_type = "Sales Invoice"
                                    reference_name = frappe.get_doc("Sales Invoice", reference.strip())
                                    if reference_name.custom_debtor_code != journal_entry[2]:
                                        writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                        skip_invoice = journal_entry[0]
                                        data ={}
                                        continue
                                elif(frappe.db.exists("Journal Entry", reference.strip())):
                                    reference_type = "Journal Entry"
                                    reference_name = frappe.get_doc("Journal Entry", reference.strip())
                                    if reference_name.debtor_code != journal_entry[2]:
                                        writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                        skip_invoice = journal_entry[0]
                                        data ={}
                                        continue
                                else:
                                    writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    continue
                            except:
                                writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14]])
                                skip_invoice = journal_entry[0]
                                continue
                            remaining_ammount += round(float(reference_amount), 2)
                            try:
                                tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": journal_entry[13]})
                            except:
                                tax_code = None
                            debtor_account = {
                                "account": debtor_account_name,
                                "party_type": "Customer",
                                "party": customer,
                                "custom_description": description or "No Description",
                                "debit_in_account_currency": 0,
                                "credit_in_account_currency": round(float(reference_amount), 2),
                                "reference_type": reference_type if reference_type else None,
                                "reference_name": reference_name.name if reference_name else None,
                                "custom_tax_code" : tax_code.name if tax_code else None,
                                "user_remark": journal_entry[9]
                            }
                            all_item.append(debtor_account)
                data = {
                    "name" : journal_entry[0],
                    "voucher_type": journal_entry[14],
                    "company" : company,
                    "custom_created_by": "System",
                    "posting_date": datetime.strptime(journal_entry[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                    "currency": currency,
                    "customer": customer,
                    "debtor_code" : journal_entry[2],
                    "user_remark": journal_entry[3],
                    "agent": journal_entry[4],
                    # "custom_tax_rate": credit_note[16] or '',
                    # "item_classification_code": credit_note[13],
                    "item_classification_code": "004",
                    # "lhdn_tax_type": credit_note[14],
                    "lhdn_tax_type": "02",
                    "custom_created_by": journal_entry[12],
                    "docstatus": 1
                }
            elif (journal_entry[14] == "Payment Entry"):
                if(frappe.db.exists("Payment Entry", journal_entry[0])):
                    skip_invoice = journal_entry[0]
                    writer.writerow(["Existed",  journal_entry[0], journal_entry[14]])
                    continue
                
                customer = get_customer(journal_entry[2])
                if not customer:
                    writer.writerow(["Customer Not Found", journal_entry[0], journal_entry[14]])
                    skip_invoice = journal_entry[0]
                    continue

                if not journal_entry[6]:
                    writer.writerow(["Income Account Not Found", journal_entry[0], journal_entry[14]])
                    skip_invoice = journal_entry[0]
                    continue

                payment_account = journal_entry[6]

                if(float(journal_entry[5]) == 0 or not journal_entry[5]):
                    writer.writerow(["Payment amount is 0", journal_entry[0], journal_entry[14]])
                    skip_invoice = journal_entry[0]
                    continue
                else:
                    try:
                        account_name = frappe.get_doc("Account", {"account_number": journal_entry[6]})
                    except:
                        writer.writerow(["Account Not Found", journal_entry[0], journal_entry[14]])
                        skip_invoice = journal_entry[0]
                        continue

                    #Find reference
                    try: #Check if sales invoice reference exists
                        if(journal_entry[9]):
                            if(journal_entry[8] == "RI" and frappe.db.exists("Sales Invoice", journal_entry[9])):
                                reference_type = "Sales Invoice"
                                reference_name = frappe.get_doc("Sales Invoice", journal_entry[9])
                                if reference_name.custom_debtor_code != journal_entry[2]:
                                    writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    data ={}
                                    continue
                            elif(journal_entry[8] == "RD" and frappe.db.exists("Journal Entry", journal_entry[9])):
                                reference_type = "Journal Entry"
                                reference_name = frappe.get_doc("Journal Entry", journal_entry[9])
                                if reference_name.debtor_code != journal_entry[2]:
                                    writer.writerow(["Wrong Debtor", journal_entry[0], journal_entry[14]])
                                    skip_invoice = journal_entry[0]
                                    data ={}
                                    continue
                            else:
                                writer.writerow(["Reference Not Found", journal_entry[0], journal_entry[14], journal_entry[9]])
                                skip_invoice = journal_entry[0]
                                data ={}
                                continue
                    except:
                        writer.writerow(["Unexpected Error Found", journal_entry[0], journal_entry[14], journal_entry[9]])
                        skip_invoice = journal_entry[0]
                        data ={}
                        continue

                    if(reference_type == "Journal Entry"):
                        reference_item = {
                            "reference_doctype": reference_type,
                            "reference_name": reference_name.name,
                            "allocated_amount": round(float(journal_entry[10]), 2)
                        }
                        all_item.append(reference_item)
                    elif(reference_type == "Sales Invoice"):
                        if round(float(journal_entry[10]), 2) > float(reference_name.outstanding_amount):
                            writer.writerow(["Reference Amount larger than total amount", journal_entry[0], journal_entry[14]])
                            skip_invoice = journal_entry[0]
                            data ={}
                            continue
                        else:
                            reference_item = {
                                "reference_doctype": reference_type,
                                "reference_name": reference_name.name,
                                "allocated_amount": round(float(journal_entry[10]), 2)
                            }
                            all_item.append(reference_item)
                debtor = frappe.get_doc("Customer", customer)
                debtor_account_name = None
                for account in debtor.accounts:
                    debtor_account_name = account.account
                    break
                if not debtor_account_name:
                    if(debtor.custom_debtor_type == "TD"):
                        debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                    elif(debtor.custom_debtor_type == "NTD"):
                        debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

                data = {
                    "name" : journal_entry[0],
                    "payment_type": "Receive",
                    "company" : company,
                    "party_type" : "Customer",
                    "posting_date": datetime.strptime(journal_entry[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
                    "debtor_code": journal_entry[2],
                    "party": customer,
                    "party_name": customer,
                    "mode_of_payment": journal_entry[3] or None,
                    "paid_from": debtor_account_name,
                    "paid_to": account_name.name,
                    "paid_from_account_currency": currency,
                    "paid_to_account_currency": currency,
                    "remark": journal_entry[7],
                    "paid_amount": round(float(journal_entry[5]), 2),
                    "received_amount": round(float(journal_entry[5]), 2),
                    "reference_no": journal_entry[12] or "No Cheque Number",
                    "reference_date": datetime.strptime(journal_entry[11], "%d/%m/%Y").strftime("%Y-%m-%d"),
                    "docstatus": 1,
                    "cost_center": "Main - LCESB",
                    "custom_remarks": 1,
                    "remarks": journal_entry[7] or "No Remarks",
                }
                if(journal_entry[9]):
                    data['remark'] += ("\nReference :" + journal_entry[9])
                continue

    #Submit last Credit Note
    if(len(data) != 0):
        if (previous_type == "Debit Note"):
            data["accounts"] = all_item
            data["tax"] = tax
            data["net_total"] = net_total
            data["custom_total_tax_amount"] = custom_total_tax_amount
            print(data)
            response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                pass
            else:
                print(response.text)
                writer.writerow(["Error", journal_entry[0], previous_type, response.text])
        elif (previous_type == "Credit Note"):
            if round(float(remaining_ammount),2) > round(float(net_total), 2):
                writer.writerow(["Reference Amount larger than total amount", previous_id, previous_type])
            elif round(float(remaining_ammount), 2) < round(float(net_total), 2):
                customer = get_customer(previous_customer)
                if not customer:
                    writer.writerow(["Customer Not Found", journal_entry[0], journal_entry[14]])
                debtor = frappe.get_doc("Customer", customer)
                debtor_account_name = None
                for account in debtor.accounts:
                    debtor_account_name = account.account
                    break
                if not debtor_account_name:
                    if(debtor.custom_debtor_type == "TD"):
                        debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                    elif(debtor.custom_debtor_type == "NTD"):
                        debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"
                remain = round(float(net_total), 2) - round(float(remaining_ammount), 2)
                debtor_account = {
                    "account": debtor_account_name,
                    "party_type": "Customer",
                    "party": customer,
                    "custom_description": previous_description or "No Description",
                    "debit_in_account_currency": 0,
                    "credit_in_account_currency": round(float(remain), 2),
                    "reference_type": None,
                    "reference_name": None,
                    "custom_tax_code" : None,
                    "user_remark": "No Reference"
                }
                all_item.append(debtor_account)
                remaining_ammount += round(float(remain), 2)
            if(round(float(remaining_ammount),2) == round(float(net_total), 2)):
                data["accounts"] = all_item
                data["tax"] = tax
                data["net_total"] = net_total
                data["custom_total_tax_amount"] = custom_total_tax_amount
                print(data)
                response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
                if response.status_code == 200:
                    pass
                else:
                    writer.writerow(["Error", previous_id, previous_type, response.text])
        elif(previous_type == "Payment Entry"):
            data["references"] = all_item
            print(data)
            response = requests.post(PEerp_url, headers=headers, data=json.dumps(data))
            if response.status_code == 200:
                pass
            else:
                writer.writerow(["Error",  journal_entry[0], previous_type, response.text])

#0       1          2            3       4        5          6           7            8         9             10   
#DocNo	DocDate	   User Remark	 AccNo   HomeDR	  HomeCR	 ProjNo	    TaxCode	      DocKey	JournalType	  CreatedUserID
def import_JE(rows, writer):
    grouped_data = defaultdict(list)
    JEerp_url = "http://localhost/api/resource/Journal%20Entry"
    for row in rows:
        id_ = row[8]
        grouped_data[id_].append(row)

    docdate = ''
    for id_, entries in grouped_data.items():
        first = entries[0]
        docdate = first[1]
        skip = False

        try:
            check = frappe.get_doc("Journal Entry", first[0])
        except:
            check = None
        if check:
            writer.writerow(["Existed",  first[0]])
            continue

        try:
            autocount_key = frappe.get_doc("Journal Entry", {"custom_autocount_dockey": first[8]})
        except frappe.DoesNotExistError:
            autocount_key = None
        if autocount_key:
            writer.writerow(["Autocount Key Existed", first[8]])
            continue

        data = {
            "name": first[0],
            "voucher_type": "Journal Entry",
            "company": company,
            "currency": currency,
            "docstatus": 1,
            "posting_date": datetime.strptime(first[1], "%d/%m/%Y").strftime("%Y-%m-%d"),
            "user_remark": first[2],
            "agent": first[4],
            "custom_created_by": first[10],
            "custom_autocount_dockey": first[8],
            "custom_journal_type": first[9],
            "accounts": []
        }

        for rowed in entries:
            try:
                account_name = frappe.get_doc("Account", {"account_number": rowed[3]})
            except:
                writer.writerow(["Account Not Found", rowed[0]])
                skip = True
                break
            tax_code = None
            try:
                tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": rowed[7]})
            except:
                tax_code = None

            if not rowed[4] or not rowed[5]:
                writer.writerow(["Debit or Credit Amount Not Found", rowed[0]])
                skip = True
                break

            cost_center = None
            if rowed[6]:
                try:
                    cost_centered = frappe.get_doc("Cost Center", rowed[6])
                    if cost_centered:
                        cost_center = cost_centered.name
                except frappe.DoesNotExistError:
                    writer.writerow(["Cost Center Not Found", rowed[0], rowed[6]])
                    skip = True
                    break
            
            account = {
                "account": account_name.name,
                "custom_description": rowed[2] or "No Description",
                "debit_in_account_currency": round(float(rowed[4]), 2),
                "credit_in_account_currency": round(float(rowed[5]), 2),
                "user_remark": rowed[11],
                "cost_center": cost_center or "Main - LCESB",
                "custom_tax_code" : tax_code.name if tax_code else None,
            }
            data["accounts"].append(account)

        if skip:
            continue
        response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            writer.writerow(["Imported", first[0]])
        else:
            writer.writerow(["Error", first[0], docdate, response.text])
            print(f"Error importing {first[0]}: {response.text}")
            
#0       1      2          3             4                5             6       7                 8                9             10          11         12        13        14        15
#DocNo	DocKey	DocDate	   User Remark	 CreatedUserID	  JournalType	Code	KnockOffDocType	  ReferenceName	   RefType	     Amount	     ProjNo	    HomeDR	  HomeCR	DEAccNo	  Description
def import_contra(rows, writer):
    grouped_data = defaultdict(list)
    JEerp_url = "http://localhost/api/resource/Journal%20Entry"
    for row in rows:
        id_ = row[1]
        grouped_data[id_].append(row)

    docdate = ''
    for id_, entries in grouped_data.items():
        first = entries[0]
        docdate = first[2]
        skip = False

        try:
            check = frappe.get_doc("Journal Entry", first[0])
        except:
            check = None
        if check:
            writer.writerow(["Existed",  first[0]])
            continue

        try:
            autocount_key = frappe.get_doc("Journal Entry", {"custom_autocount_dockey": first[1]})
        except frappe.DoesNotExistError:
            autocount_key = None
        if autocount_key:
            writer.writerow(["Autocount Key Existed", first[0], first[1]])
            continue

        data = {
            "name": first[0],
            "voucher_type": "Journal Entry",
            "company": company,
            "currency": currency,
            "docstatus": 1,
            "posting_date": datetime.strptime(first[2], "%d/%m/%Y").strftime("%Y-%m-%d"),
            "user_remark": first[3],
            "custom_created_by": first[4],
            "custom_autocount_dockey": first[1],
            "custom_journal_type": first[5],
            "accounts": []
        }

        for row in entries:
            if(row[9] == "ARReference"):
                supplier_customer = get_customer(row[6])
            elif(row[9] == "APReference"):
                supplier_customer = get_supplier(row[6])
            if not supplier_customer:
                writer.writerow(["Customer/Supplier Not Found", first[0]])
                skip = True
                break
            try:
                account_name = frappe.get_doc("Account", {"account_number": row[14]})
            except:
                writer.writerow(["Account Not Found", row[0]])
                skip = True
                break

            tax_code = None
            try:
                tax_code = frappe.get_doc("Sales Taxes and Charges Template", {"title": row[16]})
            except:
                tax_code = None

            if not row[12] or not row[13]:
                writer.writerow(["Debit or Credit Amount Not Found", row[0]])
                skip = True
                break

            if row[9] == "ARReference":
                debtor = frappe.get_doc("Customer", supplier_customer)
            elif row[9] == "APReference":
                debtor = frappe.get_doc("Supplier", supplier_customer)

            debtor_account_name = None
            for account in debtor.accounts:
                debtor_account_name = account.account
                break
            if not debtor_account_name:
                writer.writerow(["Debtor Account Not Found", row[0], row[9]])
                skip = True
                break
                # if(debtor.custom_debtor_type == "TD"):
                #     debtor_account_name = "300-0000 - TRADE DEBTORS - LCESB"
                # elif(debtor.custom_debtor_type == "NTD"):
                #     debtor_account_name = "300-1000 - NON TRADE DEBTORS - LCESB"

            try: #Check if sales invoice reference exists
                if(row[8]):
                    if(row[7] == "RI" and frappe.db.exists("Sales Invoice", row[8])):
                        reference_type = "Sales Invoice"
                        reference_name = frappe.get_doc("Sales Invoice", row[8])
                        if reference_name.custom_debtor_code != row[6]:
                            writer.writerow(["Wrong Debtor", row[0], row[6]])
                            skip = True
                            break
                    elif(row[7] == "RD" and frappe.db.exists("Journal Entry", row[8])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", row[8])
                    elif(row[7] == "PB" and frappe.db.exists("Purchase Invoice", row[8])):
                        reference_type = "Purchase Invoice"
                        reference_name = frappe.get_doc("Purchase Invoice", row[8])
                        supplier_code = frappe.get_value("Supplier", reference_name.supplier, "custom_creditor_code")
                        if supplier_code != row[6]:
                            writer.writerow(["Wrong Creditor", row[0], row[6]])
                            skip = True
                            break
                    elif(row[7] == "PD" and frappe.db.exists("Journal Entry", row[8])):
                        reference_type = "Journal Entry"
                        reference_name = frappe.get_doc("Journal Entry", row[8])
                    else:
                        writer.writerow(["Reference Not Found", row[0],"Reference:" + row[8], "Reference Type:" + row[7]])
                        skip = True
                        break
            except:
                writer.writerow(["Unexpected Error Found", row[0], "Reference:" + row[8], "Reference Type:" + row[7]])
                skip = True
                break

            account = {
                "account": account_name.name,
                "custom_description": row[15] or "No Description",
                "debit_in_account_currency": round(float(row[13]), 2),
                "credit_in_account_currency": round(float(row[12]), 2),
                "user_remark": row[15],
                "cost_center": row[11] or "Main - LCESB",
                "custom_tax_code" : tax_code.name if tax_code else None
            }
            data["accounts"].append(account)
            debtor_account = {
                "account": debtor_account_name,
                "party_type": "Customer" if row[9] == "ARReference" else "Supplier",
                "party": supplier_customer,
                "custom_description": row[15] or "No Description",
                "debit_in_account_currency": round(float(row[12]), 2),
                "credit_in_account_currency": round(float(row[13]), 2),
                "user_remark": row[15],
                "cost_center": row[11] or "Main - LCESB",
                "reference_type": reference_type if reference_type else None,
                "reference_name": reference_name.name if reference_name else None,
                "custom_tax_code" : tax_code.name if tax_code else None
            }
            data["accounts"].append(debtor_account)

        if skip:
            continue
        response = requests.post(JEerp_url, headers=headers, data=json.dumps(data))
        if response.status_code == 200:
            writer.writerow(["Imported", row[0], row[1], row[2]])
        else:
            writer.writerow(["Error", row[0], docdate, response.text])
            # print(f"Error importing {row[0]}: {response.text}")

def get_customer(debtor_code):
    try:
        customer = frappe.get_doc("Customer", {"debtor_code": debtor_code})
        return customer.name
    except frappe.DoesNotExistError:
        customer = None
        return None
    
def get_supplier(creditor_code):
    try:
        supplier = frappe.get_doc("Supplier", {"custom_creditor_code": creditor_code})
        return supplier.name
    except frappe.DoesNotExistError:
        supplier = None
        return None


def get_unique_filename(filename):
    #status file name sales_invoice_status-YYMM-###.csv
    # Get current year and month in YYMM format
    date_part = datetime.now().strftime("%y%m")
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    directory = current_dir + "/status/"
    base_filename = f"{filename}-{date_part}"
    ext = ".csv"

    counter = 1
    new_filename = f"{directory}{base_filename}-001{ext}"  # Start with 001
    
    # Loop to check existing files and increment the number
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{directory}{base_filename}-{counter:03}{ext}"  # Format as ### (e.g., 001, 002, etc.)
        counter += 1

    return new_filename

def check(rows, writer):
    for row in rows:
        try:
            if(frappe.db.exists("Journal Entry", row[0].strip())):
                writer.writerow(["Debit Note Existed", row[0]])
            else:
                writer.writerow(["Debit Note Not Existed", row[0]])
            # if(row[8] == "RI" and frappe.db.exists("Sales Invoice", row[9].strip())):
            #     writer.writerow(["Reference Existed", row[9]])
            # elif(row[8] == "RD" and frappe.db.exists("Journal Entry", row[9].strip())):
            #     writer.writerow(["Reference Existed", row[9]])
            # else:
            #     writer.writerow(["Reference Not Existed", row[9]])
            # ref = row[0]
            # if ref != ref.rstrip():
            #     row[0] += "A"
            # if(frappe.db.exists("Sales Invoice", row[0].strip())):
            #     reference_name = frappe.get_doc("Sales Invoice", row[0].strip())
            #     if(round(float(row[2]),2) == round(float(reference_name.grand_total),2)):
            #         writer.writerow(["Correct Amount", row[0], row[2] ,"Sales Invoice" , reference_name.grand_total])
            #     elif(round(float(row[2]), 2) == round(float(reference_name.rounded_total), 2)):
            #         writer.writerow(["Correct Amount", row[0], row[2] ,"Sales Invoice" , reference_name.rounded_total])
            #     else:
            #         writer.writerow(["Wrong Amount", row[0], row[2] ,"Sales Invoice" , reference_name.grand_total])
            # elif(frappe.db.exists("Journal Entry", row[9].strip())):
            #     writer.writerow(["Reference Existed", row[0], row[2] ,"Journal Entry"])
            # else:
            #     writer.writerow(["Reference Not Existed", row[0], row[2]])
        except:
            writer.writerow(["Error", row[0]])
            continue

def cancel(rows, writer):
    for row in rows:
        ref = row[0].strip()
        if ref != ref.rstrip():
            row[0] += "A"
        if(frappe.db.exists("Sales Invoice", row[0].strip())):
            reference_name = frappe.get_doc("Sales Invoice", row[0].strip())
            if reference_name.docstatus == 1:
                reference_name.cancel()
                frappe.db.commit()
                writer.writerow(["Cancelled", row[0], "Sales Invoice"])
            else:
                writer.writerow(["Already Cancelled", row[0], "Sales Invoice"])
        elif(frappe.db.exists("Journal Entry", row[0].strip())):
            reference_name = frappe.get_doc("Journal Entry", row[0].strip())
            if reference_name.docstatus == 1:
                reference_name.cancel()
                frappe.db.commit()
                writer.writerow(["Cancelled", row[0], "Journal Entry"])
            else:
                writer.writerow(["Already Cancelled", row[0], "Journal Entry"])
        else:
            writer.writerow(["Not Found", row[0], "Sales Invoice"])
    

def fetch_data(input_file, filename):
    try:
        #Track the time of the process
        start_time = time.time()

        # Open the input and output files
        output_file = get_unique_filename(filename)
        with open(input_file, mode='r') as infile, open(output_file, mode='w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            # Loop through each row in the input file
            if filename == "sales_invoice_status":
                next(reader, None)
                import_sales_invoice(reader, writer)
            elif filename == "credit_note_status":
                next(reader, None)
                import_credit_note(reader, writer)
            elif filename == "debit_note_status":
                next(reader, None)
                import_debit_note(reader, writer)
            elif filename == "payment_entry_status":
                next(reader, None)
                import_payment_entry(reader, writer)
            elif filename == "journal_entry_status":
                next(reader, None)
                import_journal_entry(reader, writer)
            elif filename == "all_entry_status":
                next(reader, None)
                all_import(reader, writer)
            elif filename == "checking_status":
                next(reader, None)
                check(reader, writer)
            elif filename == "cancel_status":
                next(reader, None)
                cancel(reader, writer)
            elif filename == "JE_status":
                next(reader, None)
                import_JE(reader, writer)
            elif filename == "contra_status":
                next(reader, None)
                import_contra(reader, writer)

            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            print(f"Process took {int(minutes)} minutes and {int(seconds):.2f} seconds.")

    except FileNotFoundError:
        print(f"The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

def import_data(data, file):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    input_file= current_dir + "/" + file
    
    if data == "Sales Invoice":
        filename = "sales_invoice_status"
        fetch_data(input_file ,filename)
    elif data == "Credit Note":
        filename = "credit_note_status"
        fetch_data(input_file, filename)
    elif data == "Debit Note":
        filename = "debit_note_status"
        fetch_data(input_file, filename)
    elif data == "Payment Entry":
        filename = "payment_entry_status"
        fetch_data(input_file, filename)
    elif data == "Journal Entry":
        filename = "journal_entry_status"
        fetch_data(input_file, filename)
    elif data == "All Entry":
        filename = "all_entry_status"
        fetch_data(input_file, filename)
    elif data == "Check":
        filename = "checking_status"
        fetch_data(input_file, filename)
    elif data == "Cancel":
        filename = "cancel_status"
        fetch_data(input_file, filename)
    elif data == "JE":
        filename = "JE_status"
        fetch_data(input_file, filename)
    elif data == "Contra":
        filename = "contra_status"
        fetch_data(input_file, filename)