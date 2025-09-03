import json
import frappe
import time
from frappe.utils.background_jobs import get_job
from myinvois.myinvois.sign_invoice import lhdn_Background
from myinvois.myinvois.sign_invoice import refresh_doc_status

@frappe.whitelist()
def send_lhdn_invois(invoices):
    """
    Enqueue the process_invoices function to process the invoices in the background
    """
    try:
        invoice_list = json.loads(invoices)
        job = frappe.enqueue(
            process_invoices, 
            queue='long', timeout=90, 
            job_name="Process LHDN Invoices",
            invoice_list=invoice_list
        )
        return {"status": "queued", "job_id": job.id}
    except Exception as e:
        frappe.log_error(f'Error queuing invoice consolidation: {e}')
        return {"status": "failed", "error": str(e)}

def process_invoices(invoice_list):
    """
    Check the status of the LHDN submission
    """
    try:
        for invoice in invoice_list:
            doc_status = frappe.db.get_value('Sales Invoice', invoice, 'status')
            if(doc_status == 'Draft' or doc_status == 'Cancelled'):
                continue

            status = frappe.db.get_value('Sales Invoice', invoice, 'custom_lhdn_status')
            if status == 'Valid':
                continue
            if status == 'Submitted' or status == 'InProgress':
                uuid = frappe.db.get_value('Sales Invoice', invoice, 'custom_uuid')
                refresh_doc_status(uuid, invoice)
                continue
            lhdn_Background(invoice)
            frappe.db.commit()
            
        time.sleep(2)
        for invoice in invoice_list:
            current_status = frappe.db.get_value('Sales Invoice', invoice, 'custom_lhdn_status')
            if current_status == 'InProgress' or current_status == 'Submitted':
                uuid = frappe.db.get_value('Sales Invoice', invoice, 'custom_uuid')
                refresh_doc_status(uuid, invoice)
                frappe.db.commit()
                time.sleep(2)
                
        frappe.logger().info("✅ LHDN invoice job completed successfully.")
    except Exception as e:
        frappe.log_error(f'Error checking LHDN status: {e}')
        return False
    
def refresh_status(invoice):
    # time.sleep(5)
    current_status = frappe.db.get_value('Sales Invoice', invoice, 'custom_lhdn_status')
    if current_status == 'InProgress' or current_status == 'Submitted':
        uuid = frappe.db.get_value('Sales Invoice', invoice, 'custom_uuid')
        refresh_doc_status(uuid, invoice)

@frappe.whitelist()
def check_invoice_job_status(job_id, invoices):
    """
    Check LHDN status of invoices
    """
    # Initialize message dictionary with empty lists for each status
    message = {
        "success": [],
        "pending": [],
        "failed": []
    }
    invoice_list = json.loads(invoices)
    
    for invoice in invoice_list:
        current_status = frappe.db.get_value('Sales Invoice', invoice, 'custom_lhdn_status')
        if current_status == 'Submitted' or current_status == 'InProgress':
            message["pending"].append(invoice)
        elif current_status == 'Valid':
            message["success"].append(invoice)
        else:
            message["failed"].append(invoice)
    return json.dumps(message)