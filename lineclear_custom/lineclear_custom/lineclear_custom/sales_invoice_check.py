import frappe

def validate_import(doc, method):
    if not doc.custom_debtor_code and doc.customer:
        debtor_code = frappe.db.get_value('Customer', doc.customer, 'debtor_code')
        doc.custom_debtor_code = debtor_code
    
    if not doc.customer and doc.custom_debtor_code:
        customer = frappe.db.get_value('Customer', {"debtor_code" : doc.custom_debtor_code}, 'customer_name')
        doc.custom_debtor_code = customer
    
    doc.save()
    