import frappe
from lhdn_consolidate_item.lhdn_consolidate_item.constants import *
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api import check_doctype_process

@frappe.whitelist(allow_guest=True)
def get_lhdn_consolidate_list(start_date, end_date, document_type, currency, source_type):
    
    # Enhancement Source Type
    doctype_data = check_doctype_process(source_type, document_type)
    item_list = []

    if doctype_data == lhdn_submission_doctype:
        # Function for consolidate Manual Import 
        item_list = frappe.get_list(doctype_data, 
                                filters=[["invoice_date", ">=", start_date],
                                         ["invoice_date", "<=", end_date],
                                         ["document_type", "=", document_type],
                                         ["currency","=",currency],
                                         ["lhdn_status","=","Not Yet Submit"], ## LHDN Status (not yet Submit)
                                         ["docstatus", "=", "1"]], ## Submitted document only
                                fields=["name","tax","sub_total_ex","total"]
                                )
    elif doctype_data == sales_invoice_doctype:
        # Function for ERPNext Sale Invoice
        item_list = frappe.get_list(doctype_data,
                                filters=[
                                    ["posting_date", ">=", start_date],
                                    ["posting_date", "<=", end_date],
                                    ["custom_lhdn_enable_control", "=", "0"],
                                    ["custom_lhdn_status", "not in", ["Valid","Rejected","InProgress","Processed","cancelled"]],
                                    ["docstatus", "=", "1"]
                                ],
                                fields=["name","total_taxes_and_charges","total","grand_total","rounded_total"]
                                )
    elif doctype_data == journal_entry_doctype and (document_type == 'Credit Note' or document_type == 'Debit Note'):
        # function for ERPNext Journal Entry
        # Account Type Accounts Receivable
        # Credit Note and Debit Note
        item_list = frappe.get_list(doctype_data,
                                    filters=[
                                        ["posting_date", ">=", start_date],
                                        ["posting_date", "<=", end_date],
                                        ["docstatus", "=", "1"],
                                        ["custom_lhdn_enable_control", "=", "0"],
                                        ["custom_lhdn_status", "not in", ["Valid","Rejected","InProgress","Processed","cancelled"]],
                                        ["voucher_type", "=", document_type],
                                        ["accounting_type", "=", "Accounts Receivable"]
                                    ],
                                    fields=["name","custom_total_tax_amount","total_amount"]
                                    )
    elif doctype_data == purchase_invoice_doctype:
        item_list = frappe.get_list(
            doctype_data,
            filters=[
                ["posting_date", ">=", start_date],
                ["posting_date", "<=", end_date],
                ["docstatus", "=", "1"],
                ["custom_lhdn_status", "not in", ["Valid","Rejected","InProgress","Processed","cancelled"]],
                ["custom_lhdn_enable_control", "=", "0"],
                ["custom_self_bill_invoice", "=", "1"]
            ],
            fields=["name","total_taxes_and_charges","total","grand_total","rounded_total"]
        )
    elif doctype_data == journal_entry_doctype and (document_type == 'Self-billed Credit Note' or document_type == 'Self-billed Debit Note'):
        # function for ERPNext Journal Entry
        # Account Type Accounts Receivable
        # Credit Note and Debit Note
        check_doc = None
        if document_type == 'Self-billed Credit Note':
            check_doc = 'Credit Note'
        else:
            check_doc = 'Debit Note'
        item_list = frappe.get_list(doctype_data,
                                    filters=[
                                        ["posting_date", ">=", start_date],
                                        ["posting_date", "<=", end_date],
                                        ["docstatus", "=", "1"],
                                        ["custom_lhdn_enable_control", "=", "0"],
                                        ["custom_lhdn_status", "not in", ["Valid","Rejected","Processed"]],
                                        ["voucher_type", "=", check_doc],
                                        ["accounting_type", "=", "Accounts Payable"]
                                    ],
                                    fields=["name","custom_total_tax_amount","total_amount"]
                                    )

    
    

    total_tax = 0.0;
    total_taxable_amount = 0.0;
    total_final_amount = 0.0;
    total_item = 0;
    final_item_list = []

    if len(item_list) > 0:
        # Manual Import Item List
        if doctype_data == lhdn_submission_doctype:
            for single_item in item_list:
                total_tax += single_item.tax
                total_taxable_amount += single_item.sub_total_ex
                total_final_amount += single_item.total
                total_item += 1
                final_item_list.append(single_item.name)
        # Sales Invoice Item list
        elif doctype_data == sales_invoice_doctype:
            for single_item in item_list:
                total_tax += single_item.total_taxes_and_charges
                total_taxable_amount += single_item.total
                if single_item.rounded_total == 0:
                    total_final_amount += single_item.grand_total
                else:
                    total_final_amount += single_item.rounded_total
                total_item += 1
                final_item_list.append(single_item.name)
        elif doctype_data == journal_entry_doctype:
            for single_item in item_list:
                total_tax+= single_item.custom_total_tax_amount
                total_taxable_amount += (single_item.total_amount - single_item.custom_total_tax_amount)
                total_final_amount += single_item.total_amount
                total_item += 1
                final_item_list.append(single_item.name)
        elif doctype_data == purchase_invoice_doctype:
            for single_item in item_list:
                total_tax += single_item.total_taxes_and_charges
                total_taxable_amount += single_item.total
                if single_item.rounded_total == 0:
                    total_final_amount += single_item.grand_total
                else:
                    total_final_amount += single_item.rounded_total
                total_item += 1
                final_item_list.append(single_item.name)
        
    total_tax  = round(abs(total_tax), 2)
    total_taxable_amount = round(abs(total_taxable_amount), 2)
    total_final_amount = round(abs(total_final_amount), 2)

    JSON_Response = {
        "total_item": total_item,
        "total_final_amount": total_final_amount,
        "total_tax_amount": total_tax,
        "total_taxable_amount": total_taxable_amount,
        "item_list": final_item_list
    }

    return JSON_Response;