from datetime import datetime, timedelta
import json
import frappe, re, requests
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_create_xml import custom_xml_tags, custom_invoice_data, invoice_Typecode_Compliance, doc_Reference, company_Data, consolidate_customer_Data, tax_Data, calculate_consolidate_amount, item_data_manual, item_data_system, generate_batch_id, xml_structuring, billing_Reference_data, consolidate_supplier_Data, company_Data_customer
import lxml.etree as MyTree
from lxml import etree
import hashlib
import base64
from urllib.parse import urlparse, urlunparse
from lhdn_consolidate_item.lhdn_consolidate_item.constants import *
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_progress_handling import ProgressTracker, StopExecution
import time

# Remark Source Code
# Ignore Naming for function and json_invoice_list or invoice, the source code initially build to consolidate invoice only, not it is able dynamically handle all document
# Now it can handle debit note, credit note, self-bill invoice, self-bill debit note, self-bill credit note, refund note and self-bill refund-note
# End of remark

def get_API_url(base_url):
    try:
        settings =  frappe.get_doc('Lhdn Settings')
        if settings.select == "Sandbox":
            url = settings.sandbox_url + base_url
        else:
            url = settings.production_url + base_url
        return url 
    except Exception as e:
        frappe.throw(" getting url failed"+ str(e) ) 

def make_qr_code_url(uuid,long_id):
    qr_code_url = get_API_url(base_url=f"/{uuid}/share/{long_id}")
    
    return qr_code_url

def check_doctype_process(source_type, document_type):
    # Enhancement Source Type
    # Dynamically assigned proper doctype to allow LHDN consolidate functiont to process data
    if source_type == source_type_manual:
        return lhdn_submission_doctype
    elif source_type == source_type_system:
        if document_type == 'Invoice':
            return sales_invoice_doctype
        if document_type == 'Credit Note' or document_type == 'Debit Note':
            return journal_entry_doctype
        if document_type == 'Self-billed Invoice':
            return purchase_invoice_doctype
        if document_type == 'Self-billed Credit Note' or document_type == 'Self-billed Debit Note':
            return journal_entry_doctype


def removeTags(finalzatcaxml):
                try:
                    #Code corrected by Farook K - ERPGulf
                    xml_file = MyTree.fromstring(finalzatcaxml)
                    xsl_file = MyTree.fromstring('''<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                                    xmlns:xs="http://www.w3.org/2001/XMLSchema"
                                    xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
                                    xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
                                    xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"
                                    xmlns:ext="urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
                                    exclude-result-prefixes="xs"
                                    version="2.0">
                                    <xsl:output omit-xml-declaration="yes" encoding="utf-8" indent="no"/>
                                    <xsl:template match="node() | @*">
                                        <xsl:copy>
                                            <xsl:apply-templates select="node() | @*"/>
                                        </xsl:copy>
                                    </xsl:template>
                                    <xsl:template match="//*[local-name()='Invoice']//*[local-name()='UBLExtensions']"></xsl:template>
                                    <xsl:template match="//*[local-name()='AdditionalDocumentReference'][cbc:ID[normalize-space(text()) = 'QR']]"></xsl:template>
                                        <xsl:template match="//*[local-name()='Invoice']/*[local-name()='Signature']"></xsl:template>
                                    </xsl:stylesheet>''')
                    transform = MyTree.XSLT(xsl_file.getroottree())
                    transformed_xml = transform(xml_file.getroottree())
                    return transformed_xml
                except Exception as e:
                                frappe.throw(" error in remove tags: "+ str(e) )


def canonicalize_xml (tag_removed_xml):
                try:
                    #Code corrected by Farook K - ERPGulf
                    canonical_xml = etree.tostring(tag_removed_xml, method="c14n").decode()
                    return canonical_xml    
                except Exception as e:
                            frappe.throw(" error in canonicalise xml: "+ str(e) )   

def getDoceHash_base64(canonicalized_xml):
    try:
        print("Enter in hash method")
        print("Next XML", canonicalized_xml)

        # Calculate SHA-256 hash of the canonicalized XML
        hash_object = hashlib.sha256(canonicalized_xml.encode())
        print("hash_object", hash_object)
        hash_hex = hash_object.hexdigest()
        print("hash_hex", hash_hex)

        # Base64 encode the canonicalized XML
        base64_encoded_xml = base64.b64encode(canonicalized_xml.encode()).decode('utf-8')
        # print("base64_encoded_xml", base64_encoded_xml)

        return hash_hex, base64_encoded_xml
    except Exception as e:
        frappe.throw("Error in Invoice hash of xml: " + str(e))

def get_invoice_version():
    settings =  frappe.get_doc('Lhdn Settings')
    invoice_version = settings.invoice_version
    return invoice_version

def remove_api_from_url(url):
    parsed_url = urlparse(url)
    settings =  frappe.get_doc('Lhdn Settings')
    if settings.select == "Sandbox":
        new_netloc = parsed_url.netloc.replace('-api', '')
    else:
        new_netloc = parsed_url.netloc.replace('api.', '')
    new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
    return new_url

@frappe.whitelist()
def get_access_token(company_name):
    # Fetch the credentials from the custom doctype
    credentials = frappe.get_doc("Lhdn Authorizations", company_name)
    client_id = credentials.client_id
    client_secret = credentials.get_password(fieldname='client_secret_key', raise_exception=False)   

    # # Check if token is already available and not expired
    if credentials.access_token and credentials.token_expiry:
        print("checking enter in first if")
        token_expiry = datetime.strptime(str(credentials.token_expiry), "%Y-%m-%d %H:%M:%S")
        print("token_expiry",token_expiry)
        if datetime.now() < token_expiry:
            print("second if")
            return credentials.access_token

    # # If token is expired or not available, request a new one
    # make url dynamic
    # get_API_url(base_url="/connect/token")
    response = requests.request("POST", url= get_API_url(base_url="/connect/token"), data={
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "InvoicingAPI"
    })

    if response.status_code == 200:
        data = response.json()
        access_token = data["access_token"]
        expires_in = data["expires_in"]
        token_expiry = datetime.now() + timedelta(seconds=expires_in)

        # Store the new token and expiry in the custom doctype
        credentials.access_token = access_token
        credentials.token_expiry = token_expiry.strftime("%Y-%m-%d %H:%M:%S")
        credentials.save()

        return access_token
    else:
        frappe.throw("Failed to fetch access token")



def compliance_api_call(encoded_hash,signed_xmlfile_name,json_invoice_list, batch_id, total_local_tax, total_final_amount, total_taxable_amount, user_email, progress_key, summary_uuid, doctype_data, source_type, document_type):
                try:
                    print("Start API call to send xml file")
                    invoice_item_list = []

                    # Enhancement to handle sales invoice, credit note and debit note
                    if doctype_data == lhdn_submission_doctype:
                        invoice_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "company"])
                    elif doctype_data == sales_invoice_doctype:
                        invoice_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "company"])
                    elif doctype_data == journal_entry_doctype:
                        invoice_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name"])
                    elif doctype_data == purchase_invoice_doctype:
                        invoice_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "company"])
                    
                    company_name = ""

                    if doctype_data != journal_entry_doctype:
                        company_name = invoice_item_list[0].company
                    else:
                        company_name = const_company_name
                                        
                    invoice_version = get_invoice_version()
                   
                    #calling token method
                    token = get_access_token(company_name)
                   
                    print("hash",encoded_hash)
                    print("xml",signed_xmlfile_name) 

                    if token:                 
                        payload = {
                                    "documents": [
                                        {
                                            "format": "XML",
                                            "documentHash": encoded_hash,
                                            "codeNumber": batch_id,
                                            "document": signed_xmlfile_name,  # Replace with actual Base64 encoded value
                                        }
                                    ]
                                }
                        payload_json = json.dumps(payload)
                        
                        headers = {
                            'accept': 'application/json',
                            'Accept-Language': 'en',
                            'X-Rate-Limit-Limit': '1000',
                            # 'Accept-Version': 'V2',
                            'Authorization': f"Bearer {token}",
                            'Content-Type': 'application/json'
                        }
                    else:
                        frappe.throw("Token for company {} not found".format(company_name))
                    try:
                        #Submit Documents Api
                        #Posting Invoice to Lhdn Portal
                        
                        MAX_RETRIES = 5
                        response = None
                        response_text = None
                        response_status_code = None

                        for attempt in range (1, MAX_RETRIES+1):
                            ## First Api
                            api_url = get_API_url(base_url=f"/api/{invoice_version}/documentsubmissions")
                            response = requests.post(api_url, headers=headers, data=payload_json)

                            response_text = response.text
                            response_status_code= response.status_code

                            if response_status_code == 202:
                                print(f"Success API call and get return result")
                                break  # Success, exit loop
                            elif response_status_code == 429:
                                wait_time = 3 ** attempt  # Exponential backoff: 2, 4, 8, 16...
                                print(f"Rate limit hit. Waiting {wait_time}s before retrying...")
                                time.sleep(wait_time)
                            else:
                                # For other errors, you may want to log and break early
                                print(f"Error submitting document: {response.text}")
                                break
                        else:
                            print(f"Max retries exceeded. Failed to submit document.")
                        
                        # # Rate Limit Handling since LHDN portal only allow 100 request call per minutes
                        # if response_status_code == 429:
                        #     tracker_id.stop_complete_error()
                        #     raise StopExecution

                        #Handling Response
                        if response_status_code == 202:
                            # Parse the JSON response
                            response_data = json.loads(response_text)
                            
                            # Extract submissionUid and uuid
                            submission_uid = response_data.get("submissionUid")
                            accepted_documents = response_data.get("acceptedDocuments", [])
                            rejected_documents = response_data.get("rejectedDocuments", [])

                            
                            #Document
                            if accepted_documents:
                                uuid = accepted_documents[0].get("uuid")

                                #Get Document Details Api call
                                api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/{uuid}/details")
                                status_api_response = requests.get(api_url, headers=headers)                                
                                print("doc status",status_api_response)
                                status_data = status_api_response.json()
                                doc_status = status_data.get("status")
                                long_id = status_data.get("longId")
                                
                                for item in invoice_item_list:
                                    item_doc = frappe.get_doc(doctype_data, item.name)

                                    # Update the Sales Invoice document with submissionUid and uuid
                                    if doctype_data == lhdn_submission_doctype:
                                        item_doc.db_set("submission_uid", submission_uid)
                                        item_doc.db_set("uuid", uuid)
                                        item_doc.db_set("long_id", long_id)
                                        item_doc.db_set('batch_id', batch_id)
                                    elif doctype_data == sales_invoice_doctype:
                                        item_doc.db_set("custom_submissionuid", submission_uid)
                                        item_doc.db_set("custom_uuid", uuid)
                                        item_doc.db_set("custom_long_id", long_id)
                                        item_doc.db_set('custom_batch_id', batch_id)
                                    elif doctype_data == journal_entry_doctype:
                                        item_doc.db_set("submission_uuid", submission_uid)
                                        item_doc.db_set("custom_uuid", uuid)
                                        item_doc.db_set("custom_long_id", long_id)
                                        item_doc.db_set("custom_batch_id", batch_id)
                                    elif doctype_data == purchase_invoice_doctype:
                                        item_doc.db_set("custom_submissionuid", submission_uid)
                                        item_doc.db_set("custom_uuid", uuid)
                                        item_doc.db_set("custom_long_id", long_id)
                                        item_doc.db_set("custom_batch_id", batch_id)
                                    

                                    if doc_status == 'Valid':
                                        if uuid and long_id:
                                            qr_code_url = make_qr_code_url(uuid,long_id)
                                            #remove -api
                                            url = remove_api_from_url(qr_code_url)

                                            if doctype_data == lhdn_submission_doctype:
                                                item_doc.db_set('lhdn_status', doc_status)
                                                item_doc.db_set('qr_code_link',url)
                                            elif doctype_data == sales_invoice_doctype:
                                                item_doc.db_set('custom_lhdn_status', doc_status)
                                                item_doc.db_set('custom_qr_code_link',url) 
                                                item_doc.db_set('custom_error_message', "") # clean error message
                                            elif doctype_data == journal_entry_doctype:
                                                item_doc.db_set('custom_lhdn_status', doc_status)
                                                item_doc.db_set('custom_qr_code_link',url)   
                                                item_doc.db_set('custom_error_message', "") # clean error message 
                                            elif doctype_data == purchase_invoice_doctype:
                                                item_doc.db_set('custom_lhdn_status', doc_status)
                                                item_doc.db_set('custom_qr_code_link',url) 
                                                item_doc.db_set('custom_error_message', "") # clean error message                                                      
                                            
                                        # frappe.msgprint(f"API Status Code: {response_status_code}<br>Document Status: {doc_status}<br>Message : QR Code Url Updated<br>Response: {response_text}")
                                    else:
                                        
                                        doc_status = "InProgress"
                                        if doctype_data == lhdn_submission_doctype:
                                            item_doc.db_set('lhdn_status', doc_status)
                                        elif doctype_data == sales_invoice_doctype:
                                            item_doc.db_set('custom_lhdn_status', doc_status)
                                            item_doc.db_set('custom_error_message', "") # clean error message
                                        elif doctype_data == journal_entry_doctype:
                                            item_doc.db_set('custom_lhdn_status', doc_status)
                                            item_doc.db_set('custom_error_message', "") # clean error message
                                        elif doctype_data == purchase_invoice_doctype:
                                            item_doc.db_set('custom_lhdn_status', doc_status)
                                            item_doc.db_set('custom_error_message', "") # clean error message

                                        # frappe.msgprint(f"API Status Code: {response_status_code}<br>Document Status: {doc_status}<br>Response: <br>{response_text}")

                                print(f"Generate Report Item")
                                generate_consolidate_summary_report_item(batch_id,json_invoice_list, total_local_tax, total_final_amount, total_taxable_amount, submission_uid, uuid, long_id, doc_status, company_name,invoice_item_list[0].name, progress_key, summary_uuid, doctype_data, source_type, document_type, user_email);

                            if rejected_documents:
                                print("enter in rejected doc")

                                # Assuming only one rejected document here:
                                rejected_doc = rejected_documents[0]
                                error = rejected_doc.get("error", {})
                                main_message = error.get("message", "")
                                details = error.get("details", [])
                                detail_messages = []
                                for detail in details:
                                    msg = detail.get("message")
                                    if msg:
                                        detail_messages.append(msg)

                                # Combine main message + details
                                all_messages = [main_message] + detail_messages
                                final_message = "\n".join(all_messages).strip()

                                for item in invoice_item_list:
                                    item_doc = frappe.get_doc(doctype_data, item.name)
                                    doc_status = "Rejected"
                                    if doctype_data == lhdn_submission_doctype:
                                        item_doc.db_set('lhdn_status', doc_status)
                                    elif doctype_data == sales_invoice_doctype:
                                        item_doc.db_set('custom_lhdn_status', doc_status)
                                        item_doc.db_set('custom_error_message',final_message)
                                    elif doctype_data == journal_entry_doctype:
                                        item_doc.db_set('custom_lhdn_status', doc_status)
                                        item_doc.db_set('custom_error_message',final_message)
                                    elif doctype_data == purchase_invoice_doctype:
                                        item_doc.db_set('custom_lhdn_status', doc_status)
                                        item_doc.db_set('custom_error_message',final_message)

                                    ## Here need to add new field remark for any reject reason
                                tracker_id = ProgressTracker(progress_key)
                                tracker_id.update_progress(False,None)
                                frappe.msgprint(f"Document Status: {doc_status}<br>Response: <br>{response_text}")
      
                        else:
                            frappe.throw("Error in complaince: " + str(response.text))    
                    
                    except Exception as e:
                        frappe.msgprint(str(e))
                        return "error in compliance", "NOT ACCEPTED"
                except Exception as e:
                    frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )


@frappe.whitelist(allow_guest=True)
def lhdn_first_checking(invoice_number_list, document_type, user_email, progress_key, summary_uuid, source_type): 
    try:
        compliance_type = 0;

        print("enter in backgorund method")
        settings = frappe.get_doc('Lhdn Settings')
        if settings.lhdn_invoice_enabled != 1:
                print("seeting enabled",settings.lhdn_invoice_enabled)
                frappe.throw("Lhdn Invoice is not enabled in Lhdn Settings, Please contact your system administrator")

        invoice_version = settings.invoice_version
        print("invoice versionnnnnnnn",invoice_version)

        # Check Compliance Version
        match document_type:
            case 'Invoice': compliance_type = 1;
            case 'Credit Note': compliance_type = 2;
            case 'Debit Note': compliance_type = 3;
            case 'Refund Note': compliance_type = 4;
            case 'Self-billed Invoice': compliance_type = 11;
            case 'Self-billed Credit Note': compliance_type = 12;
            case 'Self-billed Debit Note': compliance_type = 13;
            case 'Self-billed Refund Note': compliance_type = 14;

        ## Calling functiont to send consolidate invoices
        consolidate_invoice_call(invoice_number_list,compliance_type, user_email, progress_key, document_type, summary_uuid, source_type)
    except Exception as e:
        frappe.throw("Error in background call:  " + str(e) )

@frappe.whitelist(allow_guest=True)
def consolidate_invoice_call(invoice_number_list, compliance_type, user_email, progress_key, document_type, summary_uuid, source_type):
    try:
        print("enter in myinvoice call method")

        # Global class value
        doctype_data = check_doctype_process(source_type, document_type)

        json_invoice_list = frappe.parse_json(invoice_number_list)
        consolidate_invoice_doc = frappe.get_doc(doctype_data, json_invoice_list[0])
        total_local_tax, total_taxable_amount, total_final_amount, rounding_total = calculate_consolidate_amount(json_invoice_list, doctype_data)
        batch_id = generate_batch_id()

        # Initialize the XML document
        invoice= custom_xml_tags()

        # Fetch Sales Invoice data
        invoice = custom_invoice_data(invoice, json_invoice_list, doctype_data,batch_id)

        # Set invoice type code based on compliance type and customer type
        invoice = invoice_Typecode_Compliance(invoice, str(compliance_type))

        # Set Invoice Doc reference
        invoice = doc_Reference(invoice, consolidate_invoice_doc) 

        # Billing Reference If Invoice/Doocument Type is CN/DN
        # Billing Reference If Document Type is Self Bill CN/DN
        if document_type == "Credit Note" or document_type == "Debit Note" or document_type == 'Self-billed Credit Note' or document_type == 'Self-billed Debit Note':
            invoice = billing_Reference_data(invoice, document_type)

        # Set Supplier Information
        if document_type == "Self-billed Credit Note" or document_type == "Self-billed Debit Note" or document_type == "Self-billed Invoice":
            invoice = consolidate_supplier_Data(invoice) # Supplier Data (Consolidate List)
        else: # Debit Note / Credit Note / Invoice
            invoice = company_Data(invoice, consolidate_invoice_doc, doctype_data)   # Company data

        # Set Buyer Information
        if document_type == "Self-billed Credit Note" or document_type == "Self-billed Debit Note" or document_type == "Self-billed Invoice":
            invoice = company_Data_customer(invoice, consolidate_invoice_doc, doctype_data) # Company Data
        else: # Debit Note / Credit Note / Invoice
            invoice = consolidate_customer_Data(invoice)   # customer data (Consolidate List)
        # print("enter in else", ET.tostring(invoice, encoding='unicode'))

        # Set TaxData Information
        invoice = tax_Data(invoice,json_invoice_list,consolidate_invoice_doc,total_local_tax,total_taxable_amount,total_final_amount,rounding_total)   #invoicelevel   
        
        # Set Item Data Information
        # Manual Import Item
        if doctype_data == lhdn_submission_doctype:
            invoice = item_data_manual(invoice,json_invoice_list,batch_id, doctype_data)  # invoiceline data
        # Erpnext Sales Invoice Item
        elif doctype_data == sales_invoice_doctype or doctype_data == journal_entry_doctype or doctype_data == purchase_invoice_doctype:
            invoice = item_data_system(invoice,json_invoice_list,batch_id, doctype_data)
            
        #Convert XML to pretty string
        pretty_xml_string = xml_structuring(invoice, batch_id,doctype_data, document_type)
            
        with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
            file_content = file.read()

        tag_removed_xml = removeTags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash_hex, base64_encoded_xml = getDoceHash_base64(canonicalized_xml)

        compliance_api_call(hash_hex, base64_encoded_xml,json_invoice_list, batch_id, total_local_tax, total_final_amount, total_taxable_amount, user_email, progress_key, summary_uuid, doctype_data, source_type, document_type)
        

    except Exception as e:
        print("ERROR: " + str(e))
        frappe.log_error(title='LHDN invoice call failed', message=frappe.get_traceback())

@frappe.whitelist(allow_guest=True)
def lhdn_batch_call_async(invoice_number_list, document_type, user_email, progress_key, start_date, end_date, source_type):

    try:
        lhdn_batch_call(invoice_number_list=invoice_number_list,
            document_type=document_type,
            user_email=user_email,
            progress_key=progress_key,
            start_date=start_date,
            end_date=end_date,
            source_type=source_type)
        
    except StopExecution:
        print("Stop the whole execution due to Rate Limit Error Exceed for API Call")
     
def lhdn_batch_call(invoice_number_list, document_type, user_email, progress_key,start_date,end_date, source_type):
    json_invoice_list = frappe.parse_json(invoice_number_list)
    summary_uuid = generate_clean_final_summary_report(start_date,end_date, source_type, document_type)

    ## Check total number of interval or instance to run
    computed_batch_list, total_batches = compile_and_check_total_batches(json_invoice_list, source_type, document_type)
    ## Create Prgress tracking
    tracker_id = ProgressTracker(progress_key)
    tracker_id.set_total_items(total_batches)

    # Enqueue in loop function to let worker to pick up the function
    for item_batch_list in computed_batch_list:
        # lhdn_first_checking(
        #     invoice_number_list=item_batch_list,
        #     document_type=document_type,
        #     user_email=user_email,
        #     progress_key=progress_key,
        #     summary_uuid=summary_uuid,
        #     source_type=source_type 
        # )
        time.sleep(2)
        frappe.enqueue(
             lhdn_first_checking,
             queue='lhdn_high_priority',
             invoice_number_list=item_batch_list,
             document_type=document_type,
             user_email=user_email,
             progress_key=progress_key,
             summary_uuid=summary_uuid,
             source_type=source_type 
        )  

def create_notifcation_final_summary_report(summary_uuid,user_email):
    if not frappe.db.exists("User", {"email": user_email}):
        frappe.throw(f"User Email {user_email} does not exist.")

    # Debug Testing
    if user_email == "administratortest@gmail.com":
        user_email = "administrator" # Setup for administaror instead
    # Debug Testing

    # formated_url_message = format_notification_url_link(batch_id)
    notification = frappe.new_doc("Notification Log")
    notification.subject = f"{summary_uuid} had been created."
    notification.type = "Alert"  # Use "Alert" to show in the bell icon
    notification.document_type = e_invoice_doctype  # Optional: Link to a document
    notification.document_name = summary_uuid
    notification.from_user = frappe.session.user
    notification.email_content = f"E-Invoice Summary report had been created for {summary_uuid}"
    notification.for_user = user_email
    notification.insert(ignore_permissions=True)
    frappe.db.commit()  # Commit the transaction to save the notification

# Final Report Unique ID
def generate_summary_id(start_date, end_date, prefix="LHDN-CONSOLIDATE"):
    creation_date = datetime.now().strftime("%Y%m%d")  # Format: YYYYMMDD
    date_range = start_date.replace("-","") + "_to_" + end_date.replace("-","")
    starting_no = 1

    ## Using Database query to arrange data order by creation DESC
    last_entry_record = None
    last_entry_name = None

    try:
        last_entry_record = frappe.get_last_doc(e_invoice_doctype)
    except frappe.DoesNotExistError:
        last_entry_record = None

    if last_entry_record:
         last_entry_name = last_entry_record.name
    
    if last_entry_name:
        match = re.search(r"-(\d{2})$", last_entry_name)
        if match:
            starting_no = int(match.group(1)) + 1
        else: 
            starting_no = 1
    else:
        starting_no = 1

    running_number = f"{starting_no:02d}" ## Running number which is always start with 1 if there is no existing data and 2 digit
    summary_batch_id = f"{prefix}-{creation_date}-{date_range}-{running_number}"

    return summary_batch_id

# Function to generate Batch Item List
# This Batch item List consist of 100 item which will be sent to LHDN API
# All these batch item list will compile again into one big report 
def generate_consolidate_summary_report_item(batch_id,json_invoice_list, total_local_tax, total_final_amount, total_taxable_amount, submission_uid, uuid, long_id, doc_status, company, submission_no, progress_key, summary_uuid, doctype_data, source_type, document_type, user_email):
    
    # Generation of Summary Header Report
    single_item_info = frappe.get_doc(doctype_data, json_invoice_list[0])

    # In a consolidate submission, only same currency and document type will be group together and send as one consolidate item.
    # So Currency and document type information can str8 get from one item enough
    currency = single_item_info.currency
    date_range_value = frappe.cache().get_value(batch_id)
    
    summary_report = frappe.new_doc(lhdn_summary_doctype)
    summary_report.batch_id = batch_id
    summary_report.submission_uid = submission_uid
    summary_report.long_id = long_id
    summary_report.uuid = uuid
    summary_report.document_type = document_type
    summary_report.currency = currency
    summary_report.tax = total_local_tax
    summary_report.sub_total_ex = total_taxable_amount
    summary_report.total = total_final_amount
    summary_report.lhdn_status = doc_status
    summary_report.company = company
    summary_report.submission_no = submission_no
    summary_report.invoice_start_date = date_range_value["start_date"]
    summary_report.invoice_end_date = date_range_value["end_date"]
    summary_report.source_type = source_type
    summary_report.parent_report = summary_uuid

    tracker_id = ProgressTracker(progress_key)
    tracker_id.update_pgresstracker_uuid_email(summary_uuid,user_email)
    tracker_id.update_progress(True,batch_id)

    frappe.log_error(f"{batch_id} successful")

    if doc_status == 'Valid':
        if uuid and long_id:
            qr_code_url = make_qr_code_url(uuid,long_id)
            #remove -api
            url = remove_api_from_url(qr_code_url)
            summary_report.qr_code_link = url


    # Generation of Item List
    all_item_list = []
    
    # Manual Report Item
    if doctype_data == lhdn_submission_doctype:
        all_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["invoice_no", "debtor_code", "debtor_name", "agent", "currency", "tax", "sub_total_ex", "total"])

        for item in all_item_list:
            summary_child = summary_report.append("lhdn_table_item_list", {})
            summary_child.invoice_no = item.invoice_no
            summary_child.debtor_code = item.debtor_code
            summary_child.debtor_name = item.debtor_name
            summary_child.agent = item.agent
            summary_child.currency = item.currency
            summary_child.tax = item.tax
            summary_child.sub_total_ex = item.sub_total_ex
            summary_child.total = item.total    
    
    # Erpnext Sales Invoice Item
    elif doctype_data == sales_invoice_doctype:
        parent_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "custom_debtor_code", "currency", "agent","rounding_adjustment"])

        for item in parent_item_list:
            parent_item_doc = frappe.get_doc(doctype_data, item.name)
            child_item_list = parent_item_doc.items
            check_flag_rounding_once = 0 # default
            if item.rounding_adjustment != 0:
                check_flag_rounding_once = 1

            for child_item in child_item_list:
                summary_child = summary_report.append("lhdn_table_item_list", {})
                summary_child.invoice_no = item.name
                summary_child.debtor_code = item.custom_debtor_code
                summary_child.debtor_name = "NA"
                summary_child.agent = item.agent
                summary_child.currency = item.currency
                summary_child.tax = child_item.custom_tax_amount
                summary_child.sub_total_ex = child_item.net_amount
                # Special Handling for rounding purpose
                # Rounding will only add into one item if the following item have multiple item list
                # So final value will be tally properly
                if check_flag_rounding_once == 1:
                    summary_child.total = float(child_item.custom_tax_amount) + float(child_item.net_amount) + float(item.rounding_adjustment)
                    check_flag_rounding_once = 2 # Make flag more than 1 to prevent it run again
                else:
                    summary_child.total = float(child_item.custom_tax_amount) + float(child_item.net_amount)
                
    
    elif doctype_data == journal_entry_doctype:
        parent_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "debtor_code", "currency", "agent"])
        
        for item in parent_item_list:
            parent_item_doc = frappe.get_doc(doctype_data, item.name)
            child_item_list = parent_item_doc.custom_accounting_entires

            for child_item in child_item_list:
                summary_child = summary_report.append("lhdn_table_item_list", {})
                summary_child.invoice_no = item.name
                summary_child.debtor_code = item.debtor_code
                summary_child.debtor_name = "NA"
                summary_child.agent = item.agent
                summary_child.currency = item.currency
                summary_child.tax = child_item.tax_amount
                summary_child.sub_total_ex = child_item.amount
                summary_child.total = float(child_item.tax_amount) + float(child_item.amount)

    elif doctype_data == purchase_invoice_doctype:
        # Need to check and enhance
        parent_item_list = frappe.get_list(doctype_data, filters=[["name", "in", json_invoice_list]], fields=["name", "custom_debtor_code", "currency", "agent", "rounding_adjustment"])

        for item in parent_item_list:
            parent_item_doc = frappe.get_doc(doctype_data, item.name)
            child_item_list = parent_item_doc.items
            check_flag_rounding_once = 0 # default
            if item.rounding_adjustment != 0:
                check_flag_rounding_once = 1

            for child_item in child_item_list:
                summary_child = summary_report.append("lhdn_table_item_list", {})
                summary_child.invoice_no = item.name
                summary_child.debtor_code = "NA"
                summary_child.debtor_name = "NA"
                summary_child.agent = item.agent
                summary_child.currency = item.currency
                summary_child.tax = child_item.custom_tax_amount
                summary_child.sub_total_ex = child_item.net_amount
                # Special Handling for rounding purpose
                # Rounding will only add into one item if the following item have multiple item list
                # So final value will be tally properly
                if check_flag_rounding_once == 1:
                    summary_child.total = float(child_item.custom_tax_amount) + float(child_item.net_amount) + float(item.rounding_adjustment)
                    check_flag_rounding_once = 2 # Make flag more than 1 to prevent it run again
                else:
                    summary_child.total = float(child_item.custom_tax_amount) + float(child_item.net_amount)

    summary_report.insert(ignore_permissions=True)
    summary_report.submit()

    # Clean the cache value after finish create the batch item report
    frappe.cache().delete_value(batch_id) 

    # appened batch_item_report into final summary report
    appened_final_summary_report_item(summary_uuid, batch_id)  

# Gneration of High Level Report which will house all batch_item report
def generate_clean_final_summary_report(start_date, end_date, source_type, document_type):

    summary_uuid = generate_summary_id(start_date, end_date)

    final_summary_report = frappe.new_doc(e_invoice_doctype)
    final_summary_report.summary_batch_id = summary_uuid
    final_summary_report.lhdn_status = 'Pending'
    final_summary_report.submission_date = datetime.now().strftime("%Y-%m-%d") # dd-mm-yyyy
    final_summary_report.source_type = source_type
    final_summary_report.document_type = document_type
    final_summary_report.insert(ignore_permissions=True)
    final_summary_report.submit()

    return summary_uuid

def appened_final_summary_report_item(summary_uuid, batch_id):

    batch_item_info = frappe.get_doc(lhdn_summary_doctype, batch_id)
    final_summary_report = frappe.get_doc(e_invoice_doctype, summary_uuid)
    final_summary_report.reload()

    # Add Grand total amount, Total tax amount, total Taxable amount
    final_summary_report.grand_total += batch_item_info.total
    final_summary_report.total_tax += batch_item_info.tax
    final_summary_report.total_taxable_amount += batch_item_info.sub_total_ex

    batch_child_item = final_summary_report.append("lhdn_table_batch_item_list")
    batch_child_item.batch_id = batch_item_info.batch_id
    batch_child_item.submission_date = batch_item_info.submission_date
    batch_child_item.validation_date = batch_item_info.validation_date
    batch_child_item.currency = batch_item_info.currency
    batch_child_item.sub_total_ex = batch_item_info.sub_total_ex
    batch_child_item.tax = batch_item_info.tax
    batch_child_item.total = batch_item_info.total
    batch_child_item.document_type = batch_item_info.document_type
    batch_child_item.invoice_start_date = batch_item_info.invoice_start_date 
    batch_child_item.invoice_end_date = batch_item_info.invoice_end_date
    batch_child_item.billing_period = batch_item_info.invoice_start_date.strftime("%Y-%m-%d") + " to " + batch_item_info.invoice_end_date.strftime("%Y-%m-%d")
    batch_child_item.lhdn_status = batch_item_info.lhdn_status
    batch_child_item.uuid = batch_item_info.uuid

    try:
        final_summary_report.save(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(f"Failed to save child item: {e}")
        frappe.throw("Error saving batch item. Check logs.")

    print("Finish one cycle of lhdn_first_checking enqueue function")

def compile_and_check_total_batches(json_invoice_list,source_type,document_type):

    ## This function would help compile the batch list and pass final bacth list into lhdn_first_checking to create xml file which will send to LHDN E-invoices portal
    ## This function would compile 100 items which is belong in each batch list
    ## Since Sales Invoices each have multiple child item which cam be treated as one items, so the function would help to calculate and separate properly
    ## The final result will be final_batch_list because lhdn_first_checking function would need the name of sales invoice to create xml file for LHDN e-invoices

    # Function parameter
    final_batch_list = []
    total_batches = 0

    # Check source type
    if source_type == source_type_manual:
        ## Check total number of interval or instance to run
        total_batches = (len(json_invoice_list) + batch_size - 1) // batch_size

        for index, i in enumerate(range(0,len(json_invoice_list), batch_size), start=1):
            item_batch_list = json_invoice_list[i:i+batch_size]
            final_batch_list.append(json.dumps(item_batch_list))

    elif source_type == source_type_system:
        # Loop to compile and check item list into 100 item
        current_batch = []
        current_batch_item_count = 0


        for item in json_invoice_list:
            parent_item_list = None
            item_count = 0

            # Check Which document type and get the proper data from which doctype
            if document_type == "Invoice":
                parent_item_list = frappe.get_doc(sales_invoice_doctype, item)
                item_count = len(parent_item_list.items)

            if document_type == "Credit Note" or document_type == "Debit Note":
                parent_item_list = frappe.get_doc(journal_entry_doctype, item)
                item_count = len(parent_item_list.custom_accounting_entires)

            if document_type == 'Self-billed Invoice':
                parent_item_list = frappe.get_doc(purchase_invoice_doctype, item)
                item_count = len(parent_item_list.items)

            if document_type == 'Self-billed Credit Note' or document_type == 'Self-billed Debit Note':
                parent_item_list = frappe.get_doc(journal_entry_doctype, item)
                item_count = len(parent_item_list.custom_accounting_entires)
            
            ## Do enhancement here to handle Journal entry

            if current_batch_item_count + item_count > batch_size and current_batch:
                # Attach a batch list if the size almost exceed 100 items
                final_batch_list.append(json.dumps(current_batch))
                total_batches += 1
                # Reset the temporary batch
                current_batch = []
                current_batch_item_count = 0 
                
            current_batch.append(item)
            current_batch_item_count += item_count   
           

        # Handle last batch item if not empty
        if current_batch:
            final_batch_list.append(json.dumps(current_batch))
            total_batches += 1

    return final_batch_list, total_batches

def check_update_final_summary_report_status(progress_id):
    final_summary_report_list = frappe.get_list(e_invoice_doctype, filters=[["lhdn_status", "=", "Pending"]], fields=["summary_batch_id"])

    if final_summary_report_list:
        for item_report in final_summary_report_list:
            check_all_condition = True
            parent_doc = frappe.get_doc(e_invoice_doctype, item_report.summary_batch_id)
            child_table_data = parent_doc.get('lhdn_table_batch_item_list')

            for child_item in child_table_data:
                if child_item.lhdn_status != 'Valid':
                    check_all_condition = False
                    break

            if check_all_condition:
                parent_doc.db_set("lhdn_status", "Valid")    

    tracker_id = ProgressTracker(progress_id)
    tracker_id.mark_complete("All item had been processed.") 
    print("Success API call for Refresh status for E-invoice report status") 

@frappe.whitelist(allow_guest=True)
def finish_consolidate_refresh_function(progress_id,summary_uuid,user_email):
    print("Start Check Final process to close the consolidate process or refresh status")
    #Update Final E-Invoice Summary report
    check_update_final_summary_report_status(progress_id)
    
        
