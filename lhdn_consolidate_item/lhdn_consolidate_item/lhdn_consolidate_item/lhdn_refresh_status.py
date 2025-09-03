import frappe
from lhdn_consolidate_item.lhdn_consolidate_item.constants import *
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api import get_access_token, get_invoice_version, get_API_url, make_qr_code_url, remove_api_from_url
import requests
from datetime import datetime
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_progress_handling import setup_progress_id, ProgressTracker, StopExecution
import time

def create_notifcation_lhdn(batch_id,user_email,summary_uuid):
    if not frappe.db.exists("User", {"email": user_email}):
        frappe.throw(f"User Email {user_email} does not exist.")

    # Debug Testing
    if user_email == "administratortest@gmail.com":
        user_email = "administrator" # Setup for administaror instead
    # Debug Testing

    # formated_url_message = format_notification_url_link(batch_id)
    notification = frappe.new_doc("Notification Log")
    notification.subject = f"{batch_id} from {summary_uuid} had been updated."
    notification.type = "Alert"  # Use "Alert" to show in the bell icon
    notification.document_type = e_invoice_doctype  # Optional: Link to a document
    notification.document_name = summary_uuid
    notification.from_user = frappe.session.user
    notification.email_content = f"LHDN Status of {batch_id} had been updated successfully"
    notification.for_user = user_email
    notification.insert(ignore_permissions=True)
    frappe.db.commit()  # Commit the transaction to save the notification
        

@frappe.whitelist()
def refresh_doc_status(uuid,batch_id,isDirect,user_email,unique_progress_key):
    try:
        summary_report = frappe.get_doc(lhdn_summary_doctype, batch_id)
        company_name = summary_report.company

        MAX_RETRIES = 5
        status_response = None
        response_status_code = None

        for attempt in range (1, MAX_RETRIES+1):
            #calling token method
            token = get_access_token(company_name)

            headers = {
                    'accept': 'application/json',
                    'Accept-Language': 'en',
                    'X-Rate-Limit-Limit': '1000',
                    # 'Accept-Version': 'V2',
                    'Authorization': f"Bearer {token}",
                    'Content-Type': 'application/json'
            }
            invoice_version = get_invoice_version()
            api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/{uuid}/details")
            
            status_response = requests.get(api_url, headers=headers)
            response_status_code= status_response.status_code

            if response_status_code == 429:
                wait_time = 3 ** attempt  # Exponential backoff: 2, 4, 8, 16...
                print(f"Rate limit hit. Waiting {wait_time}s before retrying...")
                time.sleep(wait_time)
            else:
                print(f"Success API call and get return result")
                break  # Success, exit loop
        else:
            print(f"Max retries exceeded. Failed to submit document.")

        print("doc status",status_response)
        status_data = status_response.json()
        doc_status = status_data.get("status")
        long_id = status_data.get("longId")
        print("status code longid",status_data.get("longId"))
        
        #added for retrieving submission and validation datetime 
        submission_date = datetime.strptime(status_data.get("dateTimeReceived"), '%Y-%m-%dT%H:%M:%SZ')
        validation_date = datetime.strptime(status_data.get("dateTimeValidated"), '%Y-%m-%dT%H:%M:%SZ')
        summary_report.db_set("submission_date", submission_date)
        summary_report.db_set("validation_date", validation_date)
        summary_report.db_set("lhdn_status", doc_status)
        summary_report.db_set("long_id",long_id)
        summary_report.db_set("remark","") # Clean error message if success

        # Update Status Child table of E-Invoice Summary item
        child_summary_doc = frappe.get_doc(lhdn_summary_doctype_item, batch_id)
        child_summary_doc.db_set("submission_date", submission_date)
        child_summary_doc.db_set("validation_date", validation_date)
        child_summary_doc.db_set("lhdn_status", doc_status)
        child_summary_doc.db_set("remark", "") # Clean error message if success

        if doc_status == "Valid":
            if uuid and long_id:
                qr_code_url = make_qr_code_url(uuid,long_id)
                #remove -api
                url = remove_api_from_url(qr_code_url)
                
                summary_report.db_set("qr_code_link",url)
                create_notifcation_lhdn(batch_id,user_email,summary_report.parent_report)

                # Check Summary Report Source Type
                item_list = []
                if summary_report.source_type == source_type_manual:
                    item_list = frappe.get_list(lhdn_submission_doctype, filters=[["batch_id", "=", batch_id]], fields=["invoice_no"])
                    # Update Back Submission item Doctype
                    for item in item_list:
                        item_doc = frappe.get_doc(lhdn_submission_doctype, item.invoice_no)
                        item_doc.db_set("lhdn_status", doc_status)
                        item_doc.db_set("long_id", long_id)
                        item_doc.db_set("qr_code_link", url)
                
                if summary_report.source_type == source_type_system:
                    update_doc_type = None
                    if summary_report.document_type == "Invoice":
                        update_doc_type = sales_invoice_doctype
                        item_list = frappe.get_list(sales_invoice_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Credit Note" or summary_report.document_type == "Debit Note" :
                        update_doc_type = journal_entry_doctype
                        item_list = frappe.get_list(journal_entry_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Self-billed Invoice":
                        update_doc_type = purchase_invoice_doctype
                        item_list = frappe.get_list(purchase_invoice_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Self-billed Credit Note" or summary_report.document_type == "Self-billed Debit Note" :
                        update_doc_type = journal_entry_doctype
                        item_list = frappe.get_list(journal_entry_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])

                    # Update Back Submission item Doctype
                    for item in item_list:
                        item_doc = frappe.get_doc(update_doc_type, item.name)
                        item_doc.db_set("custom_lhdn_status", doc_status)
                        item_doc.db_set("custom_long_id", long_id)
                        item_doc.db_set("custom_qr_code_link", url)
                        item_doc.db_set("custom_error_message", "") # Clean error message if present

                if isDirect:
                    return batch_id
                else:
                    tracker_id = ProgressTracker(unique_progress_key) # Grab the lastest status again b4 update
                    tracker_id.update_progress(True, batch_id)
            else:
                if isDirect:
                    return batch_id
                else:
                    tracker_id = ProgressTracker(unique_progress_key) # Grab the lastest status again b4 update
                    tracker_id.update_progress(False, batch_id)
        else: 
            if doc_status == "Invalid":

                # Error Message
                status_data = status_response.json()
                validation_results = status_data.get("validationResults", [])
                validation_steps = validation_results.get("validationSteps", [])
                invalid_steps = [step for step in validation_steps if step["status"] == "Invalid"]
                messages = []

                for step in invalid_steps:
                    main_error = step.get("error", {}).get("error")
                    inner_errors = step.get("error", {}).get("innerError", [])

                    messages.append(f"{main_error}")

                    for inner in inner_errors:
                        inner_message = inner.get("error")
                        if inner_message:
                            messages.append(f"- {inner_message}")
                
                # Join to final string
                final_message = "\n".join(messages)
                summary_report.db_set("remark",final_message)

                child_summary_doc = frappe.get_doc(lhdn_summary_doctype_item, batch_id)
                child_summary_doc.db_set("remark",final_message)

                item_list = []
                if summary_report.source_type == source_type_manual:
                    item_list = frappe.get_list(lhdn_submission_doctype, filters=[["batch_id", "=", batch_id]], fields=["invoice_no"])
                    for item in item_list:
                        item_doc = frappe.get_doc(lhdn_submission_doctype, item.invoice_no)
                        item_doc.db_set("lhdn_status", doc_status)

                if summary_report.source_type == source_type_system:
                    update_doc_type = None
                    if summary_report.document_type == "Invoice":
                        update_doc_type = sales_invoice_doctype
                        item_list = frappe.get_list(sales_invoice_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Credit Note" or summary_report.document_type == "Debit Note" :
                        update_doc_type = journal_entry_doctype
                        item_list = frappe.get_list(journal_entry_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Self-billed Invoice":
                        update_doc_type = purchase_invoice_doctype
                        item_list = frappe.get_list(purchase_invoice_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])
                    elif summary_report.document_type == "Self-billed Credit Note" or summary_report.document_type == "Self-billed Debit Note" :
                        update_doc_type = journal_entry_doctype
                        item_list = frappe.get_list(journal_entry_doctype, filters=[["custom_batch_id", "=", batch_id]], fields=["name"])


                    for item in item_list:
                        item_doc = frappe.get_doc(update_doc_type, item.name)
                        item_doc.db_set("custom_lhdn_status", doc_status)
                        item_doc.db_set("custom_error_message", final_message) 

            if isDirect:
                return batch_id
            else:
                tracker_id = ProgressTracker(unique_progress_key) # Grab the lastest status again b4 update
                tracker_id.update_progress(False, batch_id)

    except Exception as e:
        print(f"refresh doc status failure: {e}")
        raise RuntimeError(f"refresh doc status failure: {e}")

def refresh_status_batch_list(unique_progress_key,user_email):
    batch_id_list = frappe.get_list(lhdn_summary_doctype, filters=[["lhdn_status", "=", "InProgress"]], fields=["batch_id","uuid"])
    tracker_id = ProgressTracker(unique_progress_key)

    try:
        ## If there is any item is being found
        if len(batch_id_list) > 0:
            total_found_item = len(batch_id_list)
            tracker_id.set_total_items(total_found_item)

            for single_item in batch_id_list:
                batch_id = single_item.batch_id
                uuid = single_item.uuid
                frappe.enqueue(
                    refresh_doc_status,
                    queue='lhdn_high_priority',
                    uuid=uuid,
                    batch_id=batch_id,
                    isDirect=False,
                    user_email=user_email,
                    unique_progress_key=unique_progress_key
                )

    except StopExecution:
        print("Execution stopped in any Rate Limit Error Occurs. Ask users to try again")

@frappe.whitelist()
def refresh_status_enqueue(user_email):
    unique_progress_key = setup_progress_id()
    refresh_status_batch_list(unique_progress_key,user_email) ## Debugging purpose
    return unique_progress_key
    
def extract_error_message(validation_results):
    for item in validation_results:
        if item.get("status") == "Invalid":
            return item.get("error", {}).get("error")
    return "No errors"

def check_update_final_summary_report_status():
    final_summary_report_list = frappe.get_list(e_invoice_doctype, filters=[["lhdn_status", "=", "Pending"]], fields=["summary_batch_id"])

    if final_summary_report_list:
        for item_report in final_summary_report_list:
            check_all_condition = True
            parent_doc = frappe.get_doc(e_invoice_doctype, item_report.summary_batch_id)
            child_table_data = parent_doc.get('lhdn_table_batch_item_list')

            for child_item in child_table_data:
                if child_item.lhdn_status == 'Pending' or child_item.lhdn_status == 'Rejected' or child_item.lhdn_status == 'InProgress':
                    check_all_condition = False
                    break

            if check_all_condition:
                parent_doc.db_set("lhdn_status", "Valid")


    