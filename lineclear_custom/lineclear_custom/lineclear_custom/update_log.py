import frappe
import requests
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse, urlunparse

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
        
@frappe.whitelist()
def get_access_token(company_name):
    # Fetch the credentials from the custom doctype
    credentials = frappe.get_doc("Lhdn Authorizations", company_name)
    client_id = credentials.client_id
    client_secret = credentials.get_password(fieldname='client_secret_key', raise_exception=False)   

    # Check if token is already available and not expired
    if credentials.access_token and credentials.token_expiry:
        token_expiry = datetime.strptime(str(credentials.token_expiry), "%Y-%m-%d %H:%M:%S")
        if datetime.now() < token_expiry:
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

@frappe.whitelist(allow_guest=True)
def get_all_submission():
    try:
        settings = frappe.get_doc('Lhdn Settings')
        invoice_version = settings.invoice_version
        
        token = get_access_token('Line Clear Express Sdn Bhd')

        if not token:
            frappe.throw("Token for company 'Line Clear Express Sdn Bhd' not found")
        
        headers = {
            'accept': 'application/json',
            'Accept-Language': 'en',
            'X-Rate-Limit-Limit': '1000',
            'Authorization': f"Bearer {token}",
            'Content-Type': 'application/json'
        }
        
        params = {
            "pageNo": 1,
            "pageSize": 50,
            "status": ["Valid", "Submitted"]
        }

        api_url = get_API_url(base_url=f"/api/{invoice_version}/documents/recent")
        response = requests.get(api_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            update_status(data)
        else:
            frappe.throw(f"API request failed: {response.status_code} - {response.text}")

    except Exception as e:
        frappe.throw(f"Unexpected Error: {str(e)}")

def update_status(data):
    invoices = data.get("result", ["internalId"])
    for record in invoices:
        print(record["typeName"], record["internalId"])
        try:
            if(frappe.db.exists("LHDN Log", record["uuid"])):
                log = frappe.get_doc("LHDN Log", record["uuid"])
                log.db_set("lhdn_status", record["status"])
                log.db_set("submission_uuid", record["submissionUid"])
                log.db_set("long_id", record["longId"])
                if record["longId"]:
                    qr_code_url = make_qr_code_url(record["uuid"], record["longId"])
                    url = remove_api_from_url(qr_code_url)
                    log.db_set("qr_code_link",url)
                submission_date_str = parse_iso_with_timezone(record["dateTimeReceived"]).strftime("%Y-%m-%d %H:%M:%S")
                # validation_date_str = parse_iso_with_timezone(record["dateTimeValidated"]).strftime("%Y-%m-%d %H:%M:%S")
                
                log.db_set("submission_date_time", submission_date_str)
                frappe.db.commit()
            else:
                submission_date_str = parse_iso_with_timezone(record["dateTimeReceived"]).strftime("%Y-%m-%d %H:%M:%S")
                doc = frappe.new_doc("LHDN Log")
                doc.name = record["uuid"]
                doc.uuid = record["uuid"]
                doc.lhdn_status = record["status"]
                doc.lhdn_status = record["status"]
                doc.submission_uuid = record["submissionUid"]
                doc.long_id = record["longId"]
                doc.submission_date_time = submission_date_str
                if record["typeName"] == "Invoice":
                    doc.invoice_type = "Sales Invoice"
                elif record["typeName"] == "Self-billed Invoic":
                    doc.invoice_type = "Purchase Invoice"
                else:
                    doc.invoice_type = "Journal Entry"
                doc.invoice_id = record["internalId"]
                
                if doc.long_id:
                    qr_code_url = make_qr_code_url(record["uuid"], record["longId"])
                    url = remove_api_from_url(qr_code_url)
                    doc.qr_code_link = url
            
                doc.insert()
                frappe.db.commit()
        except:
            print(record["internalId"] + " Not Found")
            continue
    frappe.msgprint("Done Update")

def make_qr_code_url(uuid,long_id):
        qr_code_url = get_API_url(base_url=f"/{uuid}/share/{long_id}")
        return qr_code_url

def remove_api_from_url(url):
    parsed_url = urlparse(url)
    settings =  frappe.get_doc('Lhdn Settings')
    if settings.select == "Sandbox":
        new_netloc = parsed_url.netloc.replace('-api', '')
    else:
        new_netloc = parsed_url.netloc.replace('api.', '')
    new_url = urlunparse(parsed_url._replace(netloc=new_netloc))
    return new_url

def parse_iso_with_timezone(dt_str):
    # Remove trailing Z
    dt_str = dt_str.rstrip("Z")

    # If fractional seconds exist, trim to 6 digits
    if '.' in dt_str:
        main_part, frac_part = dt_str.split('.')
        frac_part = frac_part[:6]  # Only keep up to microseconds
        dt_str = f"{main_part}.{frac_part}"
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
    else:
        fmt = "%Y-%m-%dT%H:%M:%S"

    # Parse as UTC and convert to Malaysia time
    return datetime.strptime(dt_str, fmt).replace(tzinfo=timezone.utc).astimezone(
        timezone(timedelta(hours=8))
    )