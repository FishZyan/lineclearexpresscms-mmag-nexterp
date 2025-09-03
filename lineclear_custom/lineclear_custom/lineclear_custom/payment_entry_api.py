import frappe, os, math
import frappe.utils.pdf
from frappe.utils import money_in_words, getdate

@frappe.whitelist()
def download_payment(doc_no):
    """
    Download the payment entry as a PDF.
    """
    if not doc_no:
        frappe.throw("Document number is required to download the payment.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Payment Entry", doc_no)

    doc, data = get_data(doc_no)
    template = frappe.get_template("lineclear_custom/public/template/payment_entry.html")
    delimiter = '<div style="page-break-before: always;"></div>'
    money2words = money_in_words(doc.paid_amount).upper() if doc.paid_amount else "ZERO"

    batch_size = 30
    footer_size = 6

    # calculate total pages properly
    total_rows = sum(rows_taken(doc, ref) for ref in doc.references) + footer_size
    total_pages = math.ceil(total_rows / batch_size) or 1

    rendered_html_chunks = []

    item_index = 0

    for page in range(1, total_pages + 1):
        is_last = page == total_pages
        current_batch = []
        rows_used = 0

        while item_index < len(doc.references):
            item = doc.references[item_index]
            row_cost = rows_taken(doc, item)
            item.row_cost = row_cost

            # If adding this item exceeds the page row limit, break and move to next page
            if rows_used + row_cost > (batch_size - (footer_size if is_last else 0)):
                break

            current_batch.append(item)
            rows_used += row_cost
            item_index += 1

        rendered_chunk = template.render({
            "statement_date": getdate(doc.posting_date).strftime("%d/%m/%Y"),
            "letter_head": data['letter_head'],
            "target": data['target'],
            "address": data['address'],
            "total_pages": total_pages,
            "page": page,
            "doc": doc,
            "statements": current_batch,
            "money2words": money2words[4:],
            "footer": is_last,
            "footer_size": footer_size,
            "company": str(doc.company).upper(),
        })

        rendered_html_chunks.append(rendered_chunk)

    # Join all chunks with page breaks between them
    full_html = delimiter.join(rendered_html_chunks)

    # Generate PDF
    rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

    # send the PDF as a response
    frappe.local.response.filename = f"{doc_no}.pdf"
    frappe.local.response.filecontent = rendered_pdf
    frappe.local.response.type = "download"


def get_data(doc_no):
    doc = frappe.get_doc("Payment Entry", doc_no)
    for ref in doc.references:
        ref.posting_date = frappe.db.get_value(ref.reference_doctype, ref.reference_name, "posting_date").strftime("%d/%m/%Y")

    letter_head = frappe.db.get_value(
        'Letter Head', 
        doc.letter_head,
        fieldname=['content']
    )

    supplier_columns = ['creditor_code', 'supplier_name', 'custom_registration_type', 'custom_registration_no', 'tax_id', 'supplier_primary_address', 'supplier_primary_contact']
    customer_columns = ['debtor_code', 'customer_name', 'custom_registration_type', 'custom_registration_no', 'tax_id', 'customer_primary_address', 'customer_primary_contact']
    target = frappe.db.get_value(
        'Supplier' if doc.payment_type == 'Pay' else 'Customer',
        doc.party,
        fieldname=supplier_columns if doc.payment_type == 'Pay' else customer_columns,
        as_dict=1
    )
    address = frappe.db.get_value(
        'Address',
        target.supplier_primary_address if doc.payment_type == 'Pay' else target.customer_primary_address,
        fieldname=['unit_number', 'address_line1', 'address_line2', 'city', 'state'],
        as_dict=1
    )

    contact = {}
    # Phone
    if target.mobile_no:
        contact['phone'] = target.mobile_no
    else:
        phone = frappe.db.get_value(
            'Contact Phone',
            filters={'parent': target.supplier_primary_contact if doc.payment_type == 'Pay' else target.customer_primary_contact,},
            fieldname='phone'
        )
        contact['phone'] = phone or ''

    # Email
    if target.email_id:
        contact['email'] = target.email_id
    else:
        email = frappe.db.get_value(
            'Contact Email',
            filters={'parent': target.supplier_primary_contact if doc.payment_type == 'Pay' else target.customer_primary_contact },
            fieldname='email_id'
        )
        contact['email'] = email or ''

    return doc, {
        "letter_head": letter_head,
        "target": target,
        "address": address,
        "contact": contact
    }


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


def rows_taken(doc, ref):
    # max_chars = row_max_chars - index - date - doc_no - description - total - outstanding - paid
    max_chars = 106 - 1 - 10 - len(ref.reference_name) - (12*3)
    length = len(doc.remark) if doc.remark else 0
    return max(1, math.ceil(length / max_chars))