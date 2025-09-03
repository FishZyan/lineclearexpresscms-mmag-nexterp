from datetime import datetime, timedelta
import json
import frappe
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_create_xml import custom_xml_tags, custom_invoice_data, invoice_Typecode_Compliance, doc_Reference, company_Data, consolidate_customer_Data, tax_Data, calculate_consolidate_amount, item_data, generate_batch_id, xml_structuring
import lxml.etree as MyTree
from lxml import etree
import hashlib
import base64
from urllib.parse import urlparse, urlunparse
from lhdn_consolidate_item.lhdn_consolidate_item.constants import lhdn_submission_doctype, lhdn_summary_doctype, batch_size
from lhdn_consolidate_item.lhdn_consolidate_item.lhdn_progress_handling import ProgressTracker, StopExecution

import requests


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
        print("base64_encoded_xml", base64_encoded_xml)

        return hash_hex, base64_encoded_xml
    except Exception as e:
        frappe.throw("Error in Invoice hash of xml: " + str(e))

def get_invoice_version():
    settings =  frappe.get_doc('Lhdn Settings')
    invoice_version = settings.invoice_version
    return invoice_version

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

def remove_api_from_url(url):
    parsed_url = urlparse(url)
    new_netloc = parsed_url.netloc.replace('-api', '')
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



def compliance_api_call(encoded_hash,signed_xmlfile_name,json_invoice_list, batch_id, total_local_tax, total_final_amount, total_taxable_amount, user_email, tracker_id):
                try:
                    invoice_item_list = frappe.get_list(lhdn_submission_doctype, filters=[["name", "in", json_invoice_list]], fields=["name", "tax", "sub_total_ex", "total","company"])
                    company_name = invoice_item_list[0].company
                    
                                        
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
                                            "codeNumber": invoice_item_list[0].name,
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
                        
                        ## First Api
                        api_url = get_API_url(base_url=f"/api/{invoice_version}/documentsubmissions")
                        response = requests.post(api_url, headers=headers, data=payload_json)

                        response_text = response.text
                        response_status_code= response.status_code
                        
                        # Rate Limit Handling since LHDN portal only allow 100 request call per minutes
                        if response_status_code == 429:
                            tracker_id.stop_complete_error()
                            raise StopExecution

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
                                    item_doc = frappe.get_doc(lhdn_submission_doctype, item.name)

                                    # Update the Sales Invoice document with submissionUid and uuid
                                    item_doc.db_set("submission_uid", submission_uid)
                                    item_doc.db_set("uuid", uuid)
                                    item_doc.db_set("long_id", long_id)
                                    item_doc.db_set('batch_id', batch_id)

                                    if doc_status == 'Valid':
                                        if uuid and long_id:
                                            qr_code_url = make_qr_code_url(uuid,long_id)
                                            #remove -api
                                            url = remove_api_from_url(qr_code_url)

                                            item_doc.db_set('lhdn_status', doc_status)
                                            item_doc.db_set('qr_code_link',url)
                                            
                                            create_notifcation_lhdn_submission(batch_id,user_email)
                                        # frappe.msgprint(f"API Status Code: {response_status_code}<br>Document Status: {doc_status}<br>Message : QR Code Url Updated<br>Response: {response_text}")
                                    else:
                                        
                                        doc_status = "InProgress"
                                        item_doc.db_set("lhdn_status", doc_status)
                                        create_notifcation_lhdn_submission(batch_id,user_email)
                                        # frappe.msgprint(f"API Status Code: {response_status_code}<br>Document Status: {doc_status}<br>Response: <br>{response_text}")

                                generate_consolidate_summary_report(batch_id,json_invoice_list, total_local_tax, total_final_amount, total_taxable_amount, submission_uid, uuid, long_id, doc_status, company_name,invoice_item_list[0].name, tracker_id);

                            if rejected_documents:
                                for item in invoice_item_list:
                                    item_doc = frappe.get_doc(lhdn_submission_doctype, item.name)
                                    doc_status = "Rejected"
                                    item_doc.db_set("lhdn_status", doc_status)  

                                    ## Here need to add new field remark for any reject reason
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
def lhdn_first_checking(invoice_number_list, document_type, user_email, tracker_id): 
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
        consolidate_invoice_call(invoice_number_list,compliance_type, user_email, tracker_id, document_type)
    except Exception as e:
        frappe.throw("Error in background call:  " + str(e) )

@frappe.whitelist(allow_guest=True)
def consolidate_invoice_call(invoice_number_list, compliance_type, user_email, tracker_id, document_type):
    try:
        print("enter in myinvoice call method")

        json_invoice_list = frappe.parse_json(invoice_number_list)
        consolidate_invoice_doc = frappe.get_doc(lhdn_submission_doctype, json_invoice_list[0])
        total_local_tax, total_taxable_amount, total_final_amount = calculate_consolidate_amount(json_invoice_list)
        batch_id = generate_batch_id()

        # Initialize the XML document
        invoice= custom_xml_tags()

        # Fetch Sales Invoice data
        invoice = custom_invoice_data(invoice, json_invoice_list)

        # Set invoice type code based on compliance type and customer type
        invoice = invoice_Typecode_Compliance(invoice, str(compliance_type))

        # Set Invoice Doc reference
        invoice = doc_Reference(invoice, consolidate_invoice_doc) 

        # Set Supplier Information
        invoice = company_Data(invoice, consolidate_invoice_doc)   # supplier data

        # Set Buyer Information
        invoice = consolidate_customer_Data(invoice)   # customer data
        # print("enter in else", ET.tostring(invoice, encoding='unicode'))

        # Set TaxData Information
        invoice = tax_Data(invoice,json_invoice_list,consolidate_invoice_doc,total_local_tax,total_taxable_amount,total_final_amount)   #invoicelevel   
        
        # Set Item Data Information
        invoice = item_data(invoice,json_invoice_list)  # invoiceline data
            
        #Convert XML to pretty string
        pretty_xml_string = xml_structuring(invoice, batch_id,lhdn_submission_doctype, document_type)
            
        with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
            file_content = file.read()

        tag_removed_xml = removeTags(file_content)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        hash_hex, base64_encoded_xml = getDoceHash_base64(canonicalized_xml)

        # temporary debug to check how big the xml file
        # tracker_id.update_progress(True,batch_id)
        compliance_api_call(hash_hex, base64_encoded_xml,json_invoice_list, batch_id, total_local_tax, total_final_amount, total_taxable_amount, user_email, tracker_id)
        

    except Exception as e:
        print("ERROR: " + str(e))
        frappe.log_error(title='LHDN invoice call failed', message=frappe.get_traceback())

def generate_consolidate_summary_report(batch_id,json_invoice_list, total_local_tax, total_final_amount, total_taxable_amount, submission_uid, uuid, long_id, doc_status, company, submission_no, tracker_id):
    
    # Generation of Summary Header Report
    single_item_info = frappe.get_doc(lhdn_submission_doctype, json_invoice_list[0])

    # In a consolidate submission, only same currency and document type will be group together and send as one consolidate item.
    # So Currency and document type information can str8 get from one item enough
    currency = single_item_info.currency
    document_type = single_item_info.document_type
    
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

    tracker_id.update_progress(True,batch_id)

    frappe.log_error(f"{batch_id} successful")

    if doc_status == 'Valid':
        if uuid and long_id:
            qr_code_url = make_qr_code_url(uuid,long_id)
            #remove -api
            url = remove_api_from_url(qr_code_url)
            summary_report.qr_code_link = url


    # Generation of Item List
    all_item_list = frappe.get_list(lhdn_submission_doctype, filters=[["name", "in", json_invoice_list]], fields=["invoice_no", "debtor_code", "debtor_name", "agent", "currency", "tax", "sub_total_ex", "total"])

    for item in all_item_list:
        child = summary_report.append("lhdn_table_item_list", {})
        child.invoice_no = item.invoice_no
        child.debtor_code = item.debtor_code
        child.debtor_name = item.debtor_name
        child.agent = item.agent
        child.currency = item.currency
        child.tax = item.tax
        child.sub_total_ex = item.sub_total_ex
        child.total = item.total

    summary_report.insert(ignore_permissions=True)
    summary_report.submit()

@frappe.whitelist(allow_guest=True)
def lhdn_batch_call_async(invoice_number_list, document_type, user_email, progress_key):

    try:
         
        frappe.enqueue(
            lhdn_batch_call,
            queue='long',
            invoice_number_list=invoice_number_list,
            document_type=document_type,
            user_email=user_email,
            progress_key=progress_key
        )
        
        return {"status": "queued", "message": "Batch processing started in background."}
    except StopExecution:
        print("Stop the whole execution due to Rate Limit Error Exceed for API Call")
     
def lhdn_batch_call(invoice_number_list, document_type, user_email, progress_key):
    json_invoice_list = frappe.parse_json(invoice_number_list)

    ## Check total number of interval or instance to run
    total_batches = (len(json_invoice_list) + batch_size - 1) // batch_size
    ## Create Prgress tracking
    tracker_id = ProgressTracker(progress_key)
    tracker_id.set_total_items(total_batches)

    for index, i in enumerate(range(0,len(json_invoice_list), batch_size), start=1):
        item_batch_list = json_invoice_list[i:i+batch_size]
        json_batch = json.dumps(item_batch_list)
        lhdn_first_checking(json_batch,document_type,user_email, tracker_id)
        #Update tracker progress

    tracker_id.mark_complete("All item had been processed.")     

def create_notifcation_lhdn_submission(batch_id,user_email):
    if not frappe.db.exists("User", user_email):
        frappe.throw(f"User {user_email} does not exist.")

    # formated_url_message = format_notification_url_link(batch_id)
    notification = frappe.new_doc("Notification Log")
    notification.subject = f"{batch_id} had been created."
    notification.type = "Alert"  # Use "Alert" to show in the bell icon
    notification.document_type = lhdn_summary_doctype  # Optional: Link to a document
    notification.document_name = batch_id
    notification.from_user = frappe.session.user
    notification.email_content = f"LHDN Summary had been created for {batch_id}"
    notification.for_user = user_email
    notification.insert(ignore_permissions=True)
    frappe.db.commit()  # Commit the transaction to save the notification

        

    

       
     

                        
                        
                   
