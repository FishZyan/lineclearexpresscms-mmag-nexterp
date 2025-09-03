import pandas as pd
import numpy as np
import frappe, os, time, re
from frappe.utils import flt, getdate

"""
1. disable the custom_customer's is_mandatory_field
2. ensure the existence of supplier field
3. ensure the existence of creditor_code field
"""

def import_apcredit():
    start_time = time.time()
    logger = frappe.logger("apcredit_import")
    failed_docs, failed_rows = [], []

    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "source", "apcredit_20250331.xlsx")
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_error_fixed.xlsx")
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_unbalanced_fixed.xlsx")
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_patch.xlsx")

    source_df = pd.read_excel(filepath)

    source_df.fillna('', inplace=True)

    grouped = source_df.groupby("ID")

    count = 0
    doctype = "Journal Entry"
    length = len(source_df["ID"].unique())

    for invoice_id, group in grouped:

        try:
            header = group.iloc[0]
            doc = frappe.new_doc(doctype)

            doc.name = header["ID"]
            doc.docstatus = 1
            doc.set_posting_time = 1
            doc.posting_date = header["Posting Date"]
            doc.voucher_type = header["Entry Type"]
            doc.creditor_code = header["Creditor Code"]
            doc.supplier = header["Supplier"]
            doc.accounting_type = header["Write Off Based On"]
            doc.net_total = header["Net Total"]
            doc.custom_total_tax_amount = header["Tax"]
            doc.user_remark = header["User Remark"]
            
            # References
            for _, row in group.iterrows():
                doc.append("accounts", {
                    "account": row["Account (Accounting Entries)"],
                    "party_type": row["Party Type (Accounting Entries)"],
                    "party": row["Party (Accounting Entries)"],
                    "reference_name": row["Reference Name (Accounting Entries)"],
                    "reference_type": row["Reference Type (Accounting Entries)"],
                    "custom_description": row["Description (Accounting Entries)"],
                    "ap_tax_code": row["Tax Code (Accounting Entries)"],
                    "debit_in_account_currency": row["Debit (Accounting Entries)"],
                    "credit_in_account_currency": row["Credit (Accounting Entries)"],
                    "cost_center": row["Cost Center (Accounting Entries)"] or 'Main - LCESB'
                })

            # Save & Submit
            doc.insert()
            doc = frappe.get_doc(doctype, doc.name)
            doc.submit()
            frappe.db.commit()

            count += 1
            print(f"Progressing...{count}/{length}")
            logger.info(f"✅ Imported {doc.name}")

        except Exception as e:
            failed_docs.append(invoice_id)
            failed_rows.append(group.copy())
            logger.error(f"❌ Failed to import credit {invoice_id}: {e}", exc_info=True)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"🕒 Import completed in {elapsed:.2f} seconds.")

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed credits: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        print("✅ All credit notes imported successfully.")



# helper function
def normalize_account_format(value: str) -> str:
    """
        Ensure exactly one space before and after the hyphen before 'LCESB'.
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'\s*-\s*LCESB$', ' - LCESB', value.strip())
