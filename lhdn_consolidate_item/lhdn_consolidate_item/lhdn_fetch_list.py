import frappe
from lhdn_consolidate_item.lhdn_consolidate_item.constants import lhdn_submission_doctype

@frappe.whitelist(allow_guest=True)
def get_lhdn_consolidate_list(start_date, end_date, document_type, currency):
    
    item_list = frappe.get_list(lhdn_submission_doctype, 
                                filters=[["invoice_date", ">=", start_date],
                                         ["invoice_date", "<=", end_date],
                                         ["document_type", "=", document_type],
                                         ["currency","=",currency],
                                         ["lhdn_status","=","Not Yet Submit"], ## LHDN Status (not yet Submit)
                                         ["docstatus", "=", 1]], ## Submitted document only
                                fields=["name","tax","sub_total_ex","total"]
                                )

    total_tax = 0.0;
    total_taxable_amount = 0.0;
    total_final_amount = 0.0;
    total_item = 0;
    final_item_list = []

    if len(item_list) > 0:
        for single_item in item_list:
            total_tax += single_item.tax
            total_taxable_amount += single_item.sub_total_ex
            total_final_amount += single_item.total
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