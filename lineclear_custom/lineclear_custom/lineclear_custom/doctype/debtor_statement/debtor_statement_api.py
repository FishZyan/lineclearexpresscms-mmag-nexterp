import frappe, os, math
import frappe.utils.pdf
from frappe.utils import money_in_words, getdate, add_to_date, date_diff, today


""" --------------------
    Debtor Statement
--------------------- """
def get_statement(doc_no, include_payment_details):
    statement_without_details = 'debtor_statement_without_details.sql'
    statement_with_details = 'debtor_statement_with_details.sql'

    # fetch the metadata
    doc, letter_head, customer, address, bank, department = get_metadata(doc_no)
    filename = "Debtor Statement (With Details)" if include_payment_details else "Debtor Statement"
    statement_date = get_scheduled_date(doc_no, filename)

    sql_query = statement_with_details if include_payment_details else statement_without_details
    if include_payment_details:
        sql_query = 'debtor_statement_with_details.sql'
        values = (doc.from_date, doc.to_date, doc.customer, doc.to_date)
    else:
        sql_query = 'debtor_statement_without_details.sql'
        values = (doc.from_date, doc.to_date, doc.customer, doc.to_date)

    statements = execute_sql_from_file(
        sql_query,
        values=values,
        as_dict=True
    )

    try:
        ageing = execute_sql_from_file(
            'aging_summary.sql',
            values=(doc.from_date, doc.to_date, doc.customer) + (doc.to_date,) * 12,
            as_dict=True
        )
    except Exception as e:
        frappe.throw(f"Failed to retrieve debtor statements: {e}")

    money2words = money_in_words(statements[-1].balance).upper() if statements else "ZERO"
    filepath = get_template_directory(filename)
    delimiter = '<div style="page-break-before: always;"></div>'

    batch_size = 30
    footer_size = 4
    total_records = len(statements) + footer_size

    # Calculate total pages properly
    total_pages = math.ceil(total_records / batch_size) or 1

    rendered_html_chunks = []

    for page in range(1, total_pages + 1):
        is_last = page == total_pages
        start = (page - 1) * batch_size
        end = page * batch_size if not is_last else page * batch_size - footer_size
        batch = statements[start:end]

        with open(filepath, "r", encoding="utf-8") as f:
            template_source = f.read()

            rendered_chunk = frappe.render_template(template_source,{
                "title": "DEBTOR STATEMENT",
                "statement_date": getdate(statement_date).strftime("%d/%m/%Y"),
                "letter_head": letter_head,
                "customer": customer,
                "address": address,
                "total_pages": total_pages,
                "page": page,
                "statements": batch,
                "money2words": money2words[4:],
                "ageing": ageing[:6] if ageing else None,
                "outstanding_balance": statements[-1].balance if statements else 0,
                "footer": is_last,
                "footer_size": footer_size,
                "company": str(doc.company).upper(),
                "bank": bank
            })

        rendered_html_chunks.append(rendered_chunk)

    # Join all chunks with page breaks between them
    full_html = delimiter.join(rendered_html_chunks)

    return full_html


@frappe.whitelist()
def download_statement(doc_no, include_payment_details):
    include_payment_details = True if str(include_payment_details) in ["1", "True", "true"] else False

    if not doc_no:
        frappe.throw("Document number is required to download the statement.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)
    
    try:
        full_html = get_statement(doc_no, include_payment_details)
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        # send the PDF as a response
        filename = "Debtor Statement (With Details)" if include_payment_details else "Debtor Statement"

        frappe.local.response.filename = f"{filename}.pdf"
        frappe.local.response.filecontent = rendered_pdf
        frappe.local.response.type = "download"

    except Exception as e:
        frappe.throw(f"Error generating debtor statement: {str(e)}")


@frappe.whitelist()
def send_statement(doc_no, include_payment_details):
    include_payment_details = True if str(include_payment_details) in ["1", "True", "true"] else False
    docstatus = get_docstatus(doc_no)

    if not doc_no:
        frappe.throw("Document number is required.")
    elif not docstatus:
        frappe.throw("Document must be submitted before sending email.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)

    try:
        filename = "Debtor Statement (With Details)" if include_payment_details else "Debtor Statement"
        
        update_scheduled_date(doc_no, filename)
        recipients = get_recipients(doc_no)
        full_html = get_statement(doc_no, include_payment_details)
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        mail = frappe.sendmail(
            sender='email@lineclearexpress.com',
            recipients=recipients,
            subject=f'{filename}',
            message='',
            attachments=[{
                "fname": f"{filename}.pdf",
                "fcontent": rendered_pdf
            }],
            queue_separately=False,
            delayed=False
        )

        update_sent(doc_no, filename)
        return 'Email Sent'
        
    except Exception as e:
        frappe.throw(f"Error sending debtor statement: {str(e)}")



""" --------------------
    Reminder Letter
--------------------- """
def get_reminder(doc_no, reminder):
    reminder_map = {'FIRST': '1st', 'SECOND': '2nd', 'THIRD': '3rd'}
    filename = f"{reminder.capitalize()} Reminder Letter"
    doc, letter_head, customer, address, bank, department = get_metadata(doc_no)
    total_pages, page = 1, 1

    statements = execute_sql_from_file(
        'debtor_statement_without_details.sql',
        values = (doc.from_date, doc.to_date, doc.customer, doc.to_date),
        as_dict=True
    )
    
    statement_date = get_scheduled_date(doc_no, filename)

    filepath = get_template_directory(f"{reminder.capitalize()} Reminder Letter")
    
    with open(filepath, "r", encoding="utf-8") as f:
        template_source = f.read()

        full_html = frappe.render_template(template_source,{
            "letter_head": letter_head,
            "statement_date": getdate(statement_date).strftime("%d/%m/%Y"),
            "customer": customer,
            "address": address,
            "total_pages": total_pages,
            "page": page,
            "outstanding_balance": statements[-1].balance if statements else 0,
            "company": str(doc.company).upper(),
            "bank": bank,
            "department": department
        })

    return full_html


@frappe.whitelist()
def download_reminder(doc_no, reminder):
    if not doc_no:
        frappe.throw("Document number is required to download the letter.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)

    try:
        full_html = get_reminder(doc_no, reminder)
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        # send the PDF as a response
        reminder_map = {'FIRST': '1st', 'SECOND': '2nd', 'THIRD': '3rd'}
        filename = f"{reminder_map.get(reminder)} Reminder Letter"
        frappe.local.response.filename = f"{filename}.pdf"
        frappe.local.response.filecontent = rendered_pdf
        frappe.local.response.type = "download"

    except Exception as e:
        frappe.throw(f"Error generating reminder letter: {str(e)}")


@frappe.whitelist()
def send_reminder(doc_no, reminder):
    docstatus = get_docstatus(doc_no)

    if not doc_no:
        frappe.throw("Document number is required.")
    elif not docstatus:
        frappe.throw("Document must be submitted before sending email.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)

    try:
        filename = f"{reminder} Reminder Letter"
        update_scheduled_date(doc_no, filename)

        recipients = get_recipients(doc_no)
        full_html = get_reminder(doc_no, reminder.upper())
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        # send the PDF as a response
        frappe.sendmail(
            sender='email@lineclearexpress.com',
            recipients=recipients,
            subject=f'{filename}',
            message='',
            attachments=[{
                "fname": f"{filename}.pdf",
                "fcontent": rendered_pdf
            }],
            queue_separately=False,
            delayed=False
        )

        update_sent(doc_no, filename)
        return 'Email Sent'
        
    except Exception as e:
        frappe.throw(f"Error sending reminder letter: {str(e)}")



""" --------------------
    Overdue Letter
--------------------- """
def get_overdue(doc_no):
    filename = "Overdue Letter"
    doc, letter_head, customer, address, bank, department = get_metadata(doc_no)
    statement_date = get_scheduled_date(doc_no, filename)

    try:
        statements = execute_sql_from_file(
            'debtor_statement_without_details.sql',
            values=(doc.from_date, doc.to_date, doc.customer, doc.to_date),
            as_dict=True
        )
    except Exception as e:
        frappe.throw(f"Failed to retrieve debtor statements: {e}")

    try:
        ageing = execute_sql_from_file(
            'aging_summary.sql',
            values=(doc.from_date, doc.to_date, doc.customer) + (doc.to_date,) * 12,
            as_dict=True
        )
    except Exception as e:
        frappe.throw(f"Failed to retrieve debtor statements: {e}")
    
    delimiter = '<div style="page-break-before: always;"></div>'
    rendered_html_chunks = []

    batch_size = 30
    footer_size = 7
    total_records = len(statements) + footer_size
    total_pages = math.ceil(total_records / batch_size) or 1
    outstanding_balance = statements[-1].balance if statements else 0
    money2words = money_in_words(outstanding_balance).upper() if statements else "ZERO"

    # debtor statement
    filename = "Debtor Statement"
    filepath = get_template_directory(filename)

    for page in range(1, total_pages + 1):
        start = (page - 1) * batch_size
        end = page * batch_size
        batch = statements[start:end]
    
        with open(filepath, "r", encoding="utf-8") as f:
            template_source = f.read()

            rendered_chunk = frappe.render_template(template_source, {
            "title": "OVERDUE LETTER",
            "statement_date": getdate(statement_date).strftime("%d/%m/%Y"),
            "letter_head": letter_head,
            "customer": customer,
            "address": address,
            "total_pages": total_pages + 1,
            "page": page,
            "statements": batch,
            "money2words": money2words[4:],
            "ageing": ageing if ageing else None,
            "outstanding_balance": outstanding_balance,
            "footer": False,
            "company": str(doc.company).upper(),
            "bank": bank
        })

        rendered_html_chunks.append(rendered_chunk)

    # overdue page
    filename = "Overdue Letter"
    filepath = get_template_directory(filename)

    with open(filepath, "r", encoding="utf-8") as f:
        template_source = f.read()

        rendered_chunk = frappe.render_template(template_source, {
            "letter_head": letter_head,
            "statement_date": getdate(statement_date).strftime("%d/%m/%Y"),
            "customer": customer,
            "address": address,
            "total_pages": total_pages + 1,
            "page": total_pages + 1,
            "outstanding_balance": outstanding_balance,
            "company": str(doc.company).upper(),
            "bank": bank,
            "department": department,
            "footer": True,
            "money2words": money2words,
            "outstanding_balance": outstanding_balance,
            "ageing": ageing if ageing else None,
        })
        rendered_html_chunks.append(rendered_chunk)

    # Join all chunks with page breaks between them
    full_html = delimiter.join(rendered_html_chunks)

    return full_html


@frappe.whitelist()
def download_overdue(doc_no):
    if not doc_no:
        frappe.throw("Document number is required to download the letter.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)

    try:
        full_html = get_overdue(doc_no)
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        # Send the PDF as a response
        filename = "Overdue Letter (With Statement)"
        frappe.local.response.filename = f"{filename}.pdf"
        frappe.local.response.filecontent = rendered_pdf
        frappe.local.response.type = "download"

    except Exception as e:
        frappe.throw(f"Failed to retrieve overdue letter: {e}")


@frappe.whitelist()
def send_overdue(doc_no):
    docstatus = get_docstatus(doc_no)

    if not doc_no:
        frappe.throw("Document number is required.")
    elif not docstatus:
        frappe.throw("Document must be submitted before sending email.")
    
    # clear cache for this document to ensure fresh data
    frappe.clear_document_cache("Debtor Statement", doc_no)

    try:
        filename = "Overdue Letter"
        update_scheduled_date(doc_no, filename)
        recipients = get_recipients(doc_no)
        full_html = get_overdue(doc_no)
        rendered_pdf = frappe.utils.pdf.get_pdf(full_html)

        frappe.sendmail(
            sender='email@lineclearexpress.com',
            recipients=recipients,
            subject=f'{filename}',
            message='',
            attachments=[{
                "fname": f"{filename}.pdf",
                "fcontent": rendered_pdf
            }],
            queue_separately=False,
            delayed=False
        )

        update_sent(doc_no, filename)
        return 'Email Sent'
        
    except Exception as e:
        frappe.throw(f"Error sending overdue letter: {str(e)}")



""" -------------------
    Scheduler Events
-------------------- """
@frappe.whitelist()
def schedule_notifications():

    today_date = frappe.utils.today()
    logger = frappe.logger("debtor_statement", allow_site=True, file_count=20)
    logger.info(f"Running schedule_notifications for date: {today_date}")
    logger.setLevel("INFO")

    events = frappe.db.sql(
        """
        SELECT 
            DS.name, 
            DSE.doc_name, 
            MIN(DSE.date) AS date, 
            DSE.sent 
        FROM `tabDebtor Statement` AS DS
        LEFT JOIN `tabDebtor Statement Events` AS DSE ON DS.name = DSE.parent 
        WHERE DS.docstatus = 1
            AND DS.custom_status = 'Overdue'
            AND DSE.date <= %s 
            AND DSE.sent = 0
        GROUP BY DS.name
        """,
        values=(today_date,),
        as_dict=1
    )

    logger.info(f"Total {len(events)} events to process")

    for event in events:
        try:
            if 'Debtor Statement' in event.doc_name:
                include_payment_details = True if 'With Details' in event.doc_name else False
                send_statement(event.name, include_payment_details)
            elif 'Overdue Letter' in event.doc_name:
                send_overdue(event.name)
            else:
                reminder = event.doc_name.split()[0]
                send_reminder(event.name, reminder)

            logger.info(f"{event.name} | {event.doc_name} | {event.date}")
        except Exception as e:
            logger.error(f"{event.name} | {event.doc_name} | {event.date}\n {frappe.get_traceback()}")
        finally:
            logger.setLevel("ERROR")


@frappe.whitelist()
def create_schedule_events(doc_no):
    settings = get_settings()
    documents = settings.table_files
    current_date = frappe.utils.today()

    for i, document in enumerate(documents):
        d = frappe.new_doc('Debtor Statement Events')
        d.idx = i + 1
        d.doc_name = document.file_type

        if document.skip_on_creation == 0:
            d.date = add_to_date(current_date, days=document.grace_period_days, as_string=True)

        d.parent = doc_no
        d.parenttype = 'Debtor Statement'
        d.parentfield = 'table_scheduled_events'
        d.sent = 0
        d.save()
        frappe.db.commit()

        current_date = add_to_date(current_date, days=document.grace_period_days, as_string=True)


def get_scheduled_date(doc_no, filename):
    return frappe.db.get_value(
        'Debtor Statement Events', 
        filters = {
            'parent': doc_no, 
            'doc_name': filename
        }, 
        fieldname=['date']
    )


def get_event_status(doc_no, filename):
    return frappe.db.get_value(
        'Debtor Statement Events', 
        filters={"parent": doc_no, "doc_name": filename},
        fieldname=['sent']
    )


def update_scheduled_date(doc_no, filename):
    today_date = frappe.utils.today()
    scheduled_date = get_scheduled_date(doc_no, filename)
    is_sent = get_event_status(doc_no, filename)

    if is_sent:
        new_date = scheduled_date
    elif frappe.utils.date_diff(today_date, scheduled_date) > 0:
        new_date = scheduled_date
    else:
        new_date = today_date

    frappe.db.set_value(
        "Debtor Statement Events",
        {"parent": doc_no, "doc_name": filename},
        {"date": new_date},
    )

    frappe.db.commit()


def update_sent(doc_no, filename):
    frappe.db.set_value(
        "Debtor Statement Events",
        {"parent": doc_no, "doc_name": filename},
        {"sent": 1},
    )

    frappe.db.commit()



""" --------------------
    Helper Functions
--------------------- """
def get_docstatus(doc_no) -> bool:
    doc = frappe.get_doc("Debtor Statement", doc_no)
    return doc.docstatus.is_submitted()


def get_status(doc_no) -> bool:
    doc = frappe.get_doc("Debtor Statement", doc_no)
    return doc.custom_status == 'Cleared'


def get_recipients(doc_no):
    debtor = frappe.db.get_value(
        'Debtor Statement',
        filters={'name': doc_no},
        fieldname=['customer']
    )
    contact = frappe.db.get_value(
        'Customer',
        filters={'name': debtor},
        fieldname=['customer_primary_contact']
    )
    recipients = frappe.db.get_all(
        'Contact Email', 
        filters={'parent': contact},
        fields=['email_id']
    )
    recipients = [r.email_id for r in recipients]
    if len(recipients) == 0:
        raise ValueError("No Contact Email has been setup for the debtor.")
    return recipients
    

@frappe.whitelist()
def get_settings():
    return frappe.get_doc("Debtor Statement Settings", "Debtor Statement Settings").as_dict()


@frappe.whitelist()
def get_schedule_events(doc_no):
    return frappe.db.get_all(
        "Debtor Statement Events", 
        filters={"parent": doc_no},
        fields=['doc_name'],
        order_by='idx'
    )


def get_template_directory(filename):
    filename = frappe.db.get_value(
        'Debtor Statement File',
        filters={'file_type': filename},
        fieldname=['file_directory']
    )
    
    filepath = os.path.join(
        frappe.utils.get_bench_path(),
        'sites',
        frappe.utils.get_site_path("public", "files").replace("./", ""),
        filename.replace("/files/", "")
    )
    return filepath


def get_metadata(doc_no):
    doc = frappe.get_doc("Debtor Statement", doc_no)
    letter_head = frappe.db.get_value(
        'Letter Head', 
        doc.letter_head,
        fieldname=['content']
    )
    customer = frappe.db.get_value(
        'Customer', 
        doc.customer,
        fieldname=['debtor_code', 'customer_name', 'payment_terms', 'customer_primary_address'],
        as_dict=1
    )
    address = frappe.db.get_value(
        'Address',
        customer.customer_primary_address,
        fieldname=['unit_number', 'address_line1', 'address_line2', 'city', 'state'],
        as_dict=1
    )
    bank = frappe.db.get_value(
        'Bank Account',
        doc.bank_account,
        fieldname=['bank', 'bank_account_no'],
        as_dict=1
    )
    department = frappe.db.get_value(
        'Department',
        'Credit Control Department - LCESB',
        fieldname=['parent_department', 'department_name', 'phone', 'email'],
        as_dict=1
    )
    department.parent_department = frappe.db.get_value('Department', department.parent_department, fieldname=['department_name'], as_dict=0)

    return doc, letter_head, customer, address, bank, department


def execute_sql_from_file(file_name, values=None, as_dict=False):
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