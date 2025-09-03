import frappe
from frappe.model.document import Document
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from myinvois.myinvois.sign_invoice import get_access_token, get_API_url

import json
import requests
import sys
from datetime import datetime, timedelta
import csv
import frappe
import os
import time
from collections import defaultdict

def get_unique_filename(filename):
    #status file name sales_invoice_status-YYMM-###.csv
    # Get current year and month in YYMM format
    date_part = datetime.now().strftime("%y%m")
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    directory = current_dir + "/status/"
    base_filename = f"{filename}-{date_part}"
    ext = ".csv"

    counter = 1
    new_filename = f"{directory}{base_filename}-001{ext}"  # Start with 001
    
    # Loop to check existing files and increment the number
    while os.path.exists(os.path.join(directory, new_filename)):
        new_filename = f"{directory}{base_filename}-{counter:03}{ext}"  # Format as ### (e.g., 001, 002, etc.)
        counter += 1

    return new_filename

def fetch_data(input_file):
    current_file_path = os.path.abspath(__file__)
    current_dir = os.path.dirname(current_file_path)
    input_file= current_dir + "/" + input_file
    
    try:
        #Track the time of the process
        start_time = time.time()

        # Open the input and output files
        output_file = get_unique_filename("Cancel_LHDN_Status")
        with open(input_file, mode='r') as infile, open(output_file, mode='w', newline='') as outfile:
            reader = csv.reader(infile)
            writer = csv.writer(outfile)
            
            next(reader, None)
            
            # patch_invoice(reader, writer)
            cancel_invoice(reader, writer)
            # patch_journal_entry(reader, writer)
            
            end_time = time.time()
            elapsed_time = end_time - start_time
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            print(f"Process took {int(minutes)} minutes and {int(seconds):.2f} seconds.")

    except FileNotFoundError:
        print(f"The file '{input_file}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")


def cancel_invoice(rows, writer):
        for row in rows:
            name = row[0]
            try:
                try:
                    sale_doc = frappe.get_doc("Sales Invoice", name)
                except:
                    writer.writerow(["Invoice Not Found", name])
                    continue
                company_name = sale_doc.company

                settings = frappe.get_doc('Lhdn Settings')
                invoice_version = settings.invoice_version

                api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/state/{sale_doc.custom_uuid}/state")

                #calling token method
                token = get_access_token(company_name)

                if token:          
                    payload = {
                                "status":"cancelled",
                                "reason":"some reason for cancelled document"
                            }
                    payload_json = json.dumps(payload)
                    
                    headers = {
                        'accept': 'application/json',
                        'Accept-Language': 'en',
                        'X-Rate-Limit-Limit': '1000',
                        'Authorization': f"Bearer {token}",
                        'Content-Type': 'application/json'
                    }
                else:
                    frappe.throw("Token for company {} not found".format(company_name))
                try:
                    ## Cancel Api
                    #frappe.errprint(payload_json);

                    response = requests.request("PUT", api_url, headers=headers, data=payload_json)
                    response_text = response.text
                    response_status_code = response.status_code

                    #Handling Response
                    if response_status_code == 200:
                        # Parse the JSON response
                        response_data = json.loads(response_text)
                        writer.writerow(["Invoice Cancel", name, response_data])
                        # Extract Reponse Cancel Status
                        submission_uid = response_data.get("uuid")
                        cancel_status = response_data.get("status")

                        sale_doc.db_set("custom_lhdn_status", cancel_status)
                        frappe.db.commit()
                    else:
                        print("cancel fail")
                        writer.writerow(["Invoice Fail Cancel", response])
                        frappe.throw("Error in complaince: " + str(response.text))    
                except Exception as e:
                    frappe.msgprint(str(e))
                    return "error in compliance", "NOT ACCEPTED"
            except Exception as e:
                frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )
                
def set_status(name):
    try:
        sale_doc = frappe.get_doc("Sales Invoice", name)
        sale_doc.db_set("custom_lhdn_status", "Cancelled")
        frappe.db.commit()
    except Exception as e:
        return "Error"