import frappe
from frappe.model.document import Document
from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
from myinvois.myinvois.sign_invoice import get_access_token, get_API_url

import json
import requests

class CancelInvoice(SalesInvoice):
    def on_cancel(self):
        super(CancelInvoice, self).on_cancel()

        if self.custom_uuid:

            try:
                sale_doc = frappe.get_doc("Sales Invoice", self.name)
                company_name = sale_doc.company

                settings = frappe.get_doc('Lhdn Settings')
                invoice_version = settings.invoice_version

                api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/state/{self.custom_uuid}/state")

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
                        
                        # Extract Reponse Cancel Status
                        submission_uid = response_data.get("uuid")
                        cancel_status = response_data.get("status")

                        sale_doc.db_set("custom_lhdn_status", cancel_status)

                    else:
                        frappe.throw("Error in complaince: " + str(response.text))    
                except Exception as e:
                    frappe.msgprint(str(e))
                    return "error in compliance", "NOT ACCEPTED"
            except Exception as e:
                frappe.throw("ERROR in clearance invoice ,lhdn validation:  " + str(e) )
                