import pandas as pd
import numpy as np
import frappe, os, time, re
from frappe.utils import flt, getdate

def import_appayment():
    start_time = time.time()
    logger = frappe.logger("appayment_import")
    failed_docs, failed_rows = [], []

    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "source", "appayment_20250331.xlsx")
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "appayment_error_fixed.xlsx")
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "appayment_contra_fixed.xlsx")
    source_df = pd.read_excel(filepath)

    source_df.fillna('', inplace=True)

    grouped = source_df.groupby("ID")

    count = 0
    doctype = "Payment Entry"
    length = len(source_df["ID"].unique())

    for payment_id, group in grouped:
        try:
            header = group.iloc[0]
            doc = frappe.new_doc(doctype)
            doc.name = header["ID"]
            doc.set_posting_time = 1
            doc.docstatus = header["DocStatus"]
            doc.posting_date = header["Posting Date"]
            doc.company = header["Company"]
            doc.payment_type = header["Payment Type"]
            doc.creditor_code = header["Creditor Code"]
            doc.cost_center = header["Cost Center"] or 'Main - LCESB'
            doc.mode_of_payment = header["Mode of Payment"]
            doc.party_type = header["Party Type"]
            doc.party = header["Party"]
            doc.party_name = header["Party Name"]
            doc.paid_from = header["Account Paid From"]
            doc.paid_from_account_type = header["Paid From Account Type"]
            doc.paid_from_account_currency = header["Account Currency (From)"]
            doc.paid_to = header["Account Paid To"]
            doc.paid_amount = max(0, flt(header["Paid Amount"]))
            doc.received_amount = max(0, flt(header["Received Amount"]))
            doc.total_allocated_amount = max(0, flt(header["Total Allocated Amount"]))
            doc.unallocated_amount = max(0, flt(header["Unallocated Amount"]))
            doc.reference_no = header["Cheque/Reference No"]
            doc.reference_date = header["Cheque/Reference Date"]
            doc.source_exchange_rate = 1
            doc.target_exchange_rate = 1
            
            # References
            for _, row in group.iterrows():
                doc.append("references", {
                    "reference_name": row["Name (Payment References)"],
                    "reference_doctype": row["Type (Payment References)"],
                    "allocated_amount": max(0, flt(row["Allocated (Payment References)"]))
                })

            # SPECIAL CASE: ❌ Failed to import payment <docno>: (1406, "Data too long for column 'remarks' at row #")
            if doc.name in ('PVM44407', 'PVM44408', 'PVM57394'):
                doc.custom_remarks = 1
                doc.remarks = ''

            # Save & Submit
            doc.insert()
            doc = frappe.get_doc(doctype, doc.name)
            if doc.docstatus == 1:
                doc.submit()
            frappe.db.commit()

            count += 1
            print(f"Progressing...{count}/{length}")
            logger.info(f"✅ Imported {doc.name}")

        except Exception as e:
            failed_docs.append(payment_id)
            failed_rows.append(group.copy())
            logger.error(f"❌ Failed to import payment {payment_id}: {e}", exc_info=True)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"🕒 Import completed in {elapsed:.2f} seconds.")

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed payment: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "appayment_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        print("✅ All payment imported successfully.")



# helper function
def normalize_account_format(value: str) -> str:
    """
        Ensure exactly one space before and after the hyphen before 'LCESB'.
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'\s*-\s*LCESB$', ' - LCESB', value.strip())
