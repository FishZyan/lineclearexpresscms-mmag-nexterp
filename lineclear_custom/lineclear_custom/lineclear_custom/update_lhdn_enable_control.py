import frappe

@frappe.whitelist()
def sales_invoice_set_lhdn_control(doc_no):
    try:
        #Check if invoice submitted
        sale_doc = frappe.get_doc("Sales Invoice", doc_no)
        if sale_doc.docstatus != 1:
            frappe.msgprint(f"Please submit invoice before update.")
            return
        
        #Check LHDN Status
        if (sale_doc.custom_lhdn_status == "InProgress"): 
            frappe.msgprint(f"Invoice lhdn submission in progress.")
            return
        if (sale_doc.custom_lhdn_status == "Valid"): 
            frappe.msgprint(f"Invoice is submitted to lhdn and cannot be changed.")
            return
        
        customer = frappe.get_doc("Customer", sale_doc.customer)
        if sale_doc.custom_lhdn_enable_control != customer.custom_lhdn_enable_control:
            sale_doc.db_set("custom_lhdn_enable_control", customer.custom_lhdn_enable_control)
            frappe.db.commit()
            if customer.custom_lhdn_enable_control:
                frappe.msgprint(f"Invoice: {doc_no} successfully update for individual submission.")
            else:
                frappe.msgprint(f"Invoice: {doc_no} successfully update for consolidate.")
        else:
            frappe.msgprint(f"No changes has been made.")
    except Exception as e:
        frappe.log_error(f"Unexpected Error: {str(e)}\nInvoice: {doc_no}")
        return "Error"
        
@frappe.whitelist()
def journal_entry_set_lhdn_control(doc_no):
    try:
        #Check if invoice submitted
        journal_entry = frappe.get_doc("Journal Entry", doc_no)
        if journal_entry.docstatus != 1:
            frappe.msgprint(f"Please submit invoice before update.")
            return
        
        #Check LHDN Status
        if (journal_entry.custom_lhdn_status == "InProgress"): 
            frappe.msgprint(f"Lhdn submission in progress.")
            return
        if (journal_entry.custom_lhdn_status == "Valid"): 
            frappe.msgprint(f"LHDN is submitted cannot be changed.")
            return
        
        if (journal_entry.accounting_type == "Accounts Receivable"):
            customer = frappe.get_doc("Customer", journal_entry.customer)
            if journal_entry.custom_lhdn_enable_control != customer.custom_lhdn_enable_control:
                journal_entry.db_set("custom_lhdn_enable_control", customer.custom_lhdn_enable_control)
                frappe.db.commit()
                if customer.custom_lhdn_enable_control:
                    frappe.msgprint(f"Invoice: {doc_no} successfully update for individual submission.")
                else:
                    frappe.msgprint(f"Invoice: {doc_no} successfully update for consolidate.")
            else:
                frappe.msgprint(f"No changes has been made.")
        elif (journal_entry.accounting_type == "Accounts Payable"):
            supplier = frappe.get_doc("Supplier", journal_entry.supplier)
            if journal_entry.custom_lhdn_enable_control != supplier.custom_lhdn_enable_control:
                journal_entry.db_set("custom_lhdn_enable_control", supplier.custom_lhdn_enable_control)
                frappe.db.commit()
                if supplier.custom_lhdn_enable_control:
                    frappe.msgprint(f"Invoice: {doc_no} successfully update for individual submission.")
                else:
                    frappe.msgprint(f"Invoice: {doc_no} successfully update for consolidate.")
            else:
                frappe.msgprint(f"No changes has been made.")
        
    except Exception as e:
        frappe.log_error(f"Unexpected Error: {str(e)}\nInvoice: {doc_no}")
        return "Error"