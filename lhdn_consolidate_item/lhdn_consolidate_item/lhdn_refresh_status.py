import frappe
from lhdn_consolidate_item.lhdn_consolidate_item.constants import lhdn_submission_doctype, lhdn_summary_doctype
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_consolidate_api import get_access_token, get_invoice_version, get_API_url, make_qr_code_url, remove_api_from_url
import requests
from datetime import datetime
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_progress_handling import setup_progress_id, ProgressTracker, StopExecution
import time

# def format_notification_url_link(item_id):
#     notifcation_message = f"""
#     <a href='/app/{lhdn_summary_doctype.lower().replace(" ", "-")}/{item_id}' target='_blank'>
#         LHDN Status of {item_id} had been updated successfully
#     </a>
#     """
#     return notifcation_message

def create_notifcation_lhdn(batch_id,user_email):
    if not frappe.db.exists("User", user_email):
        frappe.throw(f"User {user_email} does not exist.")

    # formated_url_message = format_notification_url_link(batch_id)
    notification = frappe.new_doc("Notification Log")
    notification.subject = f"{batch_id} had been updated."
    notification.type = "Alert"  # Use "Alert" to show in the bell icon
    notification.document_type = lhdn_summary_doctype  # Optional: Link to a document
    notification.document_name = batch_id
    notification.from_user = frappe.session.user
    notification.email_content = f"LHDN Status of {batch_id} had been updated successfully"
    notification.for_user = user_email
    notification.insert(ignore_permissions=True)
    frappe.db.commit()  # Commit the transaction to save the notification
        

@frappe.whitelist()
def refresh_doc_status(uuid,batch_id,isDirect,user_email,tracker_id):
    try:
        summary_report = frappe.get_doc(lhdn_summary_doctype, batch_id)
        item_list = frappe.get_list(lhdn_submission_doctype, filters=[["batch_id", "=", batch_id]], fields=["invoice_no"])
        company_name = summary_report.company

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
        #https://{{apiBaseUrl}}/api/v1.0/documents/51W5N1C6SCZ9AHBK39YQF03J10/details
        api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/{uuid}/details")
        status_response = requests.get(api_url, headers=headers)
        response_text = status_response.text

        print("doc status",status_response)
        status_data = status_response.json()
        doc_status = status_data.get("status")
        long_id = status_data.get("longId")
        print("status code longid",status_data.get("longId"))

        status_code = status_data.get("statusCode")

        if status_code == 429:
            tracker_id.stop_complete_error("Please try again later in few seconds. Rate Limit Exceeded for API call test")
            raise StopExecution

        #added for retrieving submission and validation datetime 
        submission_date = datetime.strptime(status_data.get("dateTimeReceived"), '%Y-%m-%dT%H:%M:%SZ')
        validation_date = datetime.strptime(status_data.get("dateTimeValidated"), '%Y-%m-%dT%H:%M:%SZ')
        summary_report.db_set("submission_date", submission_date)
        summary_report.db_set("validation_date", validation_date)
        summary_report.db_set("lhdn_status", doc_status)
        summary_report.db_set("long_id",long_id)

        if doc_status == "Valid":
            if uuid and long_id:
                qr_code_url = make_qr_code_url(uuid,long_id)
                #remove -api
                url = remove_api_from_url(qr_code_url)
                
                summary_report.db_set("qr_code_link",url)
                create_notifcation_lhdn(batch_id,user_email)

                # Update Back Submission item Doctype
                for item in item_list:
                    item_doc = frappe.get_doc(lhdn_submission_doctype, item.invoice_no)
                    item_doc.db_set("lhdn_status", doc_status)
                    item_doc.db_set("long_id", long_id)
                    item_doc.db_set("qr_code_link", url)

                if isDirect:
                    return batch_id
                else:
                    return True
            else:
                if isDirect:
                    return batch_id
                else:
                    return False
        else: 
            if doc_status == "Invalid":
                remark_message = extract_error_message(status_data.get("validationResults").get("validationSteps"))
                summary_report.db_set("remark",remark_message)

            if isDirect:
                return batch_id
            else:
                return False

    except Exception as e:
                    frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )

def refresh_status_batch_list(unique_progress_key,user_email):
    batch_id_list = frappe.get_list(lhdn_summary_doctype, filters=[["lhdn_status", "=", "InProgress"]], fields=["batch_id","uuid"])
    tracker_id = ProgressTracker(unique_progress_key)

    try:
        ## If there is any item is being found
        if len(batch_id_list) > 0:
            total_found_item = len(batch_id_list)
            tracker_id.set_total_items(total_found_item)

            for single_item in batch_id_list:
                time.sleep(2)
                batch_id = single_item.batch_id
                uuid = single_item.uuid
                result = refresh_doc_status(uuid,batch_id,False,user_email,tracker_id)
                tracker_id.update_progress(result, batch_id)
            

        
            print("Run complete")
            tracker_id.mark_complete("All item had been processed.")

        ## If there is zero item
        else:
            tracker_id.mark_complete("There is no LHDN Batch Item is In Progress. No item is being refresh status")

    except StopExecution:
        print("Execution stopped in any Rate Limit Error Occurs. Ask users to try again")

@frappe.whitelist()
def refresh_status_enqueue(user_email):
    unique_progress_key = setup_progress_id()
    # refresh_status_batch_list(unique_progress_key,user_email) ## Debugging purpose
    frappe.enqueue(refresh_status_batch_list, unique_progress_key=unique_progress_key, user_email=user_email)
    return unique_progress_key
    
def extract_error_message(validation_results):
    for item in validation_results:
        if item.get("status") == "Invalid":
            return item.get("error", {}).get("error")
    return "No errors"