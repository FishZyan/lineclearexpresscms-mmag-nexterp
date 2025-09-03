from lxml import etree
import hashlib
import base64
import lxml.etree as MyTree
from datetime import datetime
import xml.etree.ElementTree as ET
import frappe
import os

from myinvois.myinvois.bulk_createxml import xml_tags,salesinvoice_data,set_total_amounts,set_tax_type_main_form,invoice_Typecode_Simplified,invoice_Typecode_Standard,doc_Reference,additional_Reference ,company_Data,customer_Data,delivery_And_PaymentMeans,tax_Data,item_data,xml_structuring,invoice_Typecode_Compliance,delivery_And_PaymentMeans_for_Compliance,doc_Reference_compliance,get_tax_total_from_items
import pyqrcode
import binascii

from cryptography import x509
from cryptography.hazmat._oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.bindings._rust import ObjectIdentifier
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
import json
import requests
from cryptography.hazmat.primitives import serialization
# import asn1

from frappe.utils import now
import re
import xml.dom.minidom as minidom
import xml.etree.ElementTree as ET
import json
import xml.etree.ElementTree as ElementTree
from frappe.utils import execute_in_shell
import sys
import frappe 
import requests
from frappe.utils.data import  get_time
from datetime import datetime, timedelta
from urllib.parse import urlparse, urlunparse


import time



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

def getInvoiceHash(canonicalized_xml):
    try:
        print("enter in hash method")
        print("Nexxxxxxxxxxxxxxxxx xml",canonicalized_xml)
        #Code corrected by Farook K - ERPGulf
        hash_object = hashlib.sha256(canonicalized_xml.encode())
        print("hash_object",hash_object)
        hash_hex = hash_object.hexdigest()
        print("hash_hex",hash_hex)
        hash_base64 = base64.b64encode(bytes.fromhex(hash_hex)).decode('utf-8')

        print("hash_base64",hash_base64)
        # base64_encoded = base64.b64encode(hash_hex.encode()).decode()
        return hash_hex,hash_base64
    except Exception as e:
        frappe.throw(" error in Invoice hash of xml: "+ str(e) )


def xml_base64_Decode(signed_xmlfile_name):
    try:
        with open(signed_xmlfile_name, "r") as file:
            xml = file.read().lstrip()
            base64_encoded = base64.b64encode(xml.encode("utf-8"))
            base64_decoded = base64_encoded.decode("utf-8")
            return base64_decoded
    except Exception as e:
        frappe.msgprint("Error in xml base64:  " + str(e) )



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

    print("response",response)

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



def get_invoice_version():
    settings =  frappe.get_doc('Lhdn Settings')
    invoice_version = settings.invoice_version
    return invoice_version


@frappe.whitelist()     
def refresh_doc_status(uuid,invoice_number):
    try:
        print("enter in refersh")
        sale_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_name = sale_doc.company
        long_id = sale_doc.custom_long_id

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
        
        #added for retrieving submission and validation datetime 
        submission_date = datetime.strptime(status_data.get("dateTimeReceived"), '%Y-%m-%dT%H:%M:%SZ')
        validation_date = datetime.strptime(status_data.get("dateTimeValidated"), '%Y-%m-%dT%H:%M:%SZ')
        sale_doc.db_set("submission_date", submission_date)
        sale_doc.db_set("validation_date", validation_date)

        sale_doc.db_set("custom_lhdn_status", doc_status)
        sale_doc.db_set("custom_error_message", status_data.get("errorMessage"))

        if doc_status == "Valid":
            if uuid and long_id:
                qr_code_url = make_qr_code_url(uuid,long_id)
                #remove -api
                url = remove_api_from_url(qr_code_url)
                
                sale_doc.db_set("custom_qr_code_link",url)
                sale_doc.db_set("custom_error_message", '') 
                # frappe.msgprint("Qr Code Updated")
                # frappe.msgprint(f"Status: {doc_status}<br>Message : QR Code Url Updated<br>Response: {response_text}")
        elif doc_status == "Rejected" or doc_status == "Invalid":
            get_error_message(invoice_number, status_response)
        else:
            frappe.msgprint(f"Status: {doc_status}<br>Message : QR Code Url Updated<br>Response: {response_text}")
    except Exception as e:
        frappe.log_error(f'Error in refresh_doc_status: {e}')   
        # frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )

def get_error_message(invoice_number, status_response):
    try:
        status_data = status_response.json()
        sale_doc = frappe.get_doc("Sales Invoice", invoice_number)
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
        sale_doc.db_set("custom_error_message", final_message)
    except:
        frappe.log_error("Error in get_error_message function for invoice: {}".format(invoice_number))

def remove_api_from_url(url):
    parsed_url = urlparse(url)
    settings =  frappe.get_doc('Lhdn Settings')
    if settings.select == "Sandbox":
        new_netloc = parsed_url.netloc.replace('-api', '')
    else:
        new_netloc = parsed_url.netloc.replace('api.', '')
    new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
    return new_url

def compliance_api_call(encoded_hash,signed_xmlfile_name,invoice_number):
    try:        
        sale_doc = frappe.get_doc("Sales Invoice", invoice_number)
        company_name = sale_doc.company
        invoice_version = get_invoice_version()
                   
        #calling token method
        token = get_access_token(company_name)         
        print("xml",signed_xmlfile_name) 

        if token:                 
            payload = {
                "documents": [
                    {
                        "format": "XML",
                        "documentHash": encoded_hash,
                        "codeNumber": invoice_number,
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
            ## First Api
            api_url = get_API_url(base_url=f"/api/{invoice_version}/documentsubmissions")
            response = requests.post(api_url, headers=headers, data=payload_json)

            response_text = response.text
            response_status_code= response.status_code

            print("checking reposnse",response_text)

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
                    print ("enter in accepted doc")
                    uuid = accepted_documents[0].get("uuid")
                                
                    # Update the Sales Invoice document with submissionUid and uuid
                    sale_doc.db_set("custom_submissionuid", submission_uid)  
                    sale_doc.db_set("custom_uuid", uuid) 

                    #Get Document Details Api call
                    #https://{{apiBaseUrl}}/api/v1.0/documents/51W5N1C6SCZ9AHBK39YQF03J10/details
                    api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/{uuid}/details")
                    status_api_response = requests.get(api_url, headers=headers)                                
                    print("doc status",status_api_response)
                    status_data = status_api_response.json()

                    doc_status = status_data.get("status")
                    long_id = status_data.get("longId")
                    sale_doc.db_set("custom_long_id", long_id)

                    #{envbaseurl}/uuid-of-document/share/longid
                    #https://preprod.myinvois.hasil.gov.my/GFSV5S3DR07TMXCS7033GA3J10/share/NZR8D94N3JW93KKX7033GA3J10hr8g6D1721560566"

                    if doc_status == 'Valid':
                        print("enter in valid")
                        if uuid and long_id:
                            qr_code_url = make_qr_code_url(uuid,long_id)
                            #remove -api
                            url = remove_api_from_url(qr_code_url)
                                        
                            sale_doc.db_set("custom_lhdn_status", doc_status)
                            sale_doc.db_set("custom_qr_code_link",url)
                            sale_doc.db_set("custom_error_message", '') 
                    else:
                        print("enter in else validation")
                        doc_status = "InProgress"
                        sale_doc.db_set("custom_lhdn_status", doc_status)
                        sale_doc.db_set("custom_error_message", '')
                                
                if rejected_documents:
                    print("enter in rejected doc")

                    doc_status = "Rejected"
                    sale_doc.db_set("custom_lhdn_status", doc_status)

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

                    sale_doc.db_set("custom_error_message", final_message)

            else:
                frappe.throw("Error in complaince: " + str(response.text))    
                    
        except Exception as e:
            frappe.msgprint(str(e))
            return "error in compliance", "NOT ACCEPTED"
    except Exception as e:
        frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )

def make_qr_code_url(uuid,long_id):
        qr_code_url = get_API_url(base_url=f"/{uuid}/share/{long_id}")
    
        return qr_code_url


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



@frappe.whitelist(allow_guest=True)          
# def myinvois_Background_on_submit(doc, method=None):              
def lhdn_Background(invoice_number):
    try:
        # sales_invoice_doc = doc
        # invoice_number = sales_invoice_doc.name
        print(invoice_number)
        sales_invoice_doc= frappe.get_doc("Sales Invoice",invoice_number )

        if sales_invoice_doc.docstatus != 1:
            frappe.log_error("Please submit the invoice before sending to Lhdn:  " + str(invoice_number))
            return
        if(sales_invoice_doc.custom_lhdn_status == "Valid" or sales_invoice_doc.custom_lhdn_status == "Processed"):
            frappe.log_error("Invoice is already Validated or Processed, Please check the status of the invoice")
            return
        if not sales_invoice_doc.custom_lhdn_enable_control:
            frappe.log_error("Lhdn Invoice is not enabled for this invoice, Please check the invoice type or contact your system administrator")
            return
        settings = frappe.get_doc('Lhdn Settings')
        invoice_version = settings.invoice_version

        if settings.lhdn_invoice_enabled != 1:
            frappe.log_error("Lhdn Invoice is not enabled in Lhdn Settings, Please contact your system administrator")
            return
        
        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.log_error("Please save and submit the invoice before sending to Lhdn:  " + str(invoice_number))
            return    
                        
        myinvois_Call(invoice_number,1)
                        
    except Exception as e:
        frappe.throw("Error in background call:  " + str(e) )


# working on b2b
#compliance_type is invoice_type
 
@frappe.whitelist(allow_guest=True)
def myinvois_Call(invoice_number, compliance_type):
    try:
        print("enter in myinvoice call method")

        compliance_type = 1
        # any_item_has_tax_template = False

        if not frappe.db.exists("Sales Invoice", invoice_number):
            frappe.log_error("Invoice Number is NOT Valid: " + str(invoice_number))
            return
        
        # Initialize the XML document
        # invoice = ET.Element("Invoice")
        invoice= xml_tags()
        # print(ET.tostring(invoice, encoding='unicode'))
        
        # Fetch Sales Invoice data
        invoice, sales_invoice_doc = salesinvoice_data(invoice, invoice_number)
        # print(ET.tostring(invoice, encoding='unicode'))        

        # Fetch Customer data
        customer_doc = frappe.get_doc("Customer", sales_invoice_doc.customer)
        print("customer", customer_doc)

        # Set invoice type code based on compliance type and customer type
        # compliance type = B2B / B2C / B2G
        if compliance_type == "0":
            # print("enter in if")
            if customer_doc.custom_b2c == 1:
                invoice = invoice_Typecode_Simplified(invoice, sales_invoice_doc)
            else:
                invoice = invoice_Typecode_Standard(invoice, sales_invoice_doc)
        else:  # if it is a compliance test
            # print ("compiance type check")
            compliance_type = "1"
            invoice = invoice_Typecode_Compliance(invoice, compliance_type)
            # print("enter in else", ET.tostring(invoice, encoding='unicode'))


        invoice = doc_Reference(invoice, sales_invoice_doc, invoice_number)   # invoice currency code
        # print("enter in else", ET.tostring(invoice, encoding='unicode'))

        invoice = company_Data(invoice, sales_invoice_doc)   # supplier data
        # print("Company Data",ET.tostring(invoice, encoding='unicode'))

        invoice = customer_Data(invoice, sales_invoice_doc)   # customer data
        # print("enter in else", ET.tostring(invoice, encoding='unicode'))
    
        invoice = tax_Data(invoice, sales_invoice_doc)   #invoicelevel   
        
        invoice=item_data(invoice,sales_invoice_doc)  # invoiceline data


        #Convert XML to pretty string
        pretty_xml_string = xml_structuring(invoice, sales_invoice_doc)
        #print(pretty_xml_string)

        # ###########################
        # #Starting code with new git
        # ##########################
        with open(frappe.local.site + "/private/files/finalzatcaxml.xml", 'r') as file:
                                    file_content = file.read()
        
        #print("file_content",file_content)
        tag_removed_xml = removeTags(file_content)
        #print("tag_removed_xml",tag_removed_xml)
        canonicalized_xml = canonicalize_xml(tag_removed_xml)
        #print("canonicalized_xml",canonicalized_xml)

        # hash1, encoded_hash = getInvoiceHash(canonicalized_xml)
        hash_hex, base64_encoded_xml = getDoceHash_base64(canonicalized_xml)
        # print("hash1",hash_hex)
        # compliance_api_call(encoded_hash, signed_xmlfile_name)
        
        compliance_api_call(hash_hex, base64_encoded_xml,invoice_number)



        # # You might want to return or save the pretty_xml_string as needed
        # # return pretty_xml_string

    except Exception as e:
        return False
        frappe.log_error(title='LHDN invoice call failed', message=get_traceback())