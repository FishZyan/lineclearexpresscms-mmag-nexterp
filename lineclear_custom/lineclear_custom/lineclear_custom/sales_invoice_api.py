import frappe, os, math
import frappe.utils.pdf
from frappe.utils import money_in_words, getdate


@frappe.whitelist()
def download_invoice(doc_no):
    """
    Download the sales invoice as a PDF.
    """
    if not doc_no:
        frappe.throw("Document number is required to download the invoice.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Sales Invoice", doc_no)

    doc, letter_head, customer, address, contact = get_metadata(doc_no)
    template = frappe.get_template("lineclear_custom/public/template/sales_invoice.html")
    delimiter = '<div style="page-break-before: always;"></div>'
    money2words = money_in_words(doc.grand_total if doc.disable_rounded_total == 1 else doc.rounded_total).upper() if doc.grand_total else "ZERO"

    batch_size = 34
    footer_size = 16

    # calculate total pages properly
    total_rows = sum(rows_taken(item) for item in doc.items) + footer_size
    total_pages = math.ceil(total_rows / batch_size) or 1

    rendered_html_chunks = []

    item_index = 0

    for page in range(1, total_pages + 1):
        is_last = page == total_pages
        current_batch = []
        rows_used = 0

        while item_index < len(doc.items):
            item = doc.items[item_index]
            row_cost = rows_taken(item)
            item.row_cost = row_cost

            # If adding this item exceeds the page row limit, break and move to next page
            if rows_used + row_cost > (batch_size - (footer_size if is_last else 0)):
                break

            current_batch.append(item)
            rows_used += row_cost
            item_index += 1

        rendered_chunk = template.render({
                "statement_date": getdate(doc.posting_date).strftime("%d/%m/%Y"),
                "letter_head": letter_head,
                "invoice_no": doc_no,
                "customer": customer,
                "address": address,
                "contact": contact,
                "total_pages": total_pages,
                "page": page,
                "statements": current_batch,
                "money2words": money2words[4:],
                "doc": doc,
                "footer": is_last,
                "company": str(doc.company).upper(),
        })
        rendered_html_chunks.append(rendered_chunk)

    # join all chunks with page breaks between them
    full_html = delimiter.join(rendered_html_chunks)

    # generate PDF
    rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

    # send the PDF as a response
    frappe.local.response.filename = f"{doc_no}.pdf"
    frappe.local.response.filecontent = rendered_pdf
    frappe.local.response.type = "download"


def get_metadata(doc_no):
    doc = frappe.get_doc("Sales Invoice", doc_no)
    # if doc.custom_qr_code_link:
    #     doc.custom_qr_code_link = doc.custom_qr_code_link.replace('api.', '')

    letter_head = frappe.db.get_value(
        'Letter Head', 
        doc.letter_head,
        fieldname=['content']
    )
    customer = frappe.db.get_value(
        'Customer',
        doc.customer,
        fieldname=['debtor_code', 'customer_name', 'payment_terms', 'sst_exemption', 'custom_sst_registration_no', 'sst_subtype', 'custom_registration_type', 'custom_registration_no', 'tax_id', 'customer_primary_address', 'customer_primary_contact'],
        as_dict=1
    )
    address = frappe.db.get_value(
        'Address',
        customer.customer_primary_address,
        fieldname=['unit_number', 'address_line1', 'address_line2', 'city', 'state'],
        as_dict=1
    )

    contact = {}
    # Phone
    if customer.mobile_no:
        contact['phone'] = customer.mobile_no
    else:
        phone = frappe.db.get_value(
            'Contact Phone',
            filters={'parent': customer.customer_primary_contact},
            fieldname='phone'
        )
        contact['phone'] = phone or ''

    # Email
    if customer.email_id:
        contact['email'] = customer.email_id
    else:
        email = frappe.db.get_value(
            'Contact Email',
            filters={'parent': customer.customer_primary_contact},
            fieldname='email_id'
        )
        contact['email'] = email or ''

    # batch id exists if invoice is submitted to consolidate e-invoice
    if doc.custom_batch_id:
        customer.tax_id = 'EI00000000010'

    return doc, letter_head, customer, address, contact


def execute_sql_from_file(file_name, values=None, as_dict=False):
    """
        execute SQL query from a file with optional parameters
    """
    filepath = os.path.join(frappe.get_app_path('lineclear_custom'), 'public', 'sql', file_name)
    
    if not isinstance(values, (list, tuple)):
        values = (values,)
    
    with open(filepath, 'r') as f:
        queries = f.read().split(';')

    results = []

    for query in queries:
        query = query.strip()
        if not query:
            continue
            
        # Special handling for IN clause with a tuple of values
        if "IN (%s)" in query:
            # Create placeholders for each item in the tuple
            placeholders = ', '.join(['%s'] * len(values))
            # Replace the single %s with the correct number of placeholders
            query = query.replace("IN (%s)", f"IN ({placeholders})")
            # Use the actual tuple values directly
            try:
                result = frappe.db.sql(query, values=values, as_dict=as_dict)
                results.append(result)
            except Exception as e:
                frappe.log_error(f"SQL Error: {str(e)}\nQuery: {query}\nValues: {values}", "SQL Execution Error")
                raise
            continue
    
        if '%s' in query:
            try:
                result = frappe.db.sql(query, values=values, as_dict=as_dict)
                results.append(result)
            except Exception as e:
                frappe.log_error(f"SQL Error: {str(e)}\nQuery: {query}\nValues: {values}", "SQL Execution Error")
                raise
        else:
            if query:
                try:
                    result = frappe.db.sql(query, as_dict=as_dict)
                    results.append(result)
                except Exception as e:
                    frappe.log_error(f"SQL Error: {str(e)}\nQuery: {query}", "SQL Execution Error")
                    raise
    
    return results[-1]


def rows_taken(item, max_chars=40):
    length = len(item.description) if item.description else 0
    return max(1, math.ceil(length / max_chars))