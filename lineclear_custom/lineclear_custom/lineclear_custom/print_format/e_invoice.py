import frappe

@frappe.whitelist()
def generate_custom_print_format(docname):
    # Fetch the Sales Invoice document
    doc = frappe.get_doc("Sales Invoice", docname)

    # Set the variable to hide the header for specific conditions
    hide_header = True  # Set this condition based on your logic

    # Render the custom print format and pass the 'hide_header' variable
    return frappe.render_template("lineclear_custom/print_format/e_invoice_tax.html", {
        'doc': doc, 
        'hide_header': hide_header  # Pass the variable to control the header
    })
