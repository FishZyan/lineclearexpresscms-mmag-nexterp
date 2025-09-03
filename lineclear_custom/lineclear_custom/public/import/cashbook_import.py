import pandas as pd
import numpy as np
import frappe, os, time, re
from frappe.utils import flt, getdate


def import_cashbook():
    start_time = time.time()
    logger = frappe.logger("cashbook_import")
    failed_docs, failed_rows = [], []

    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "cashbook_20250331.xlsx")
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "cashbook_error_fixed.xlsx")
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "cashbook_20250331_unmatch_fixed.xlsx")
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
            doc.company = header["Company"]
            doc.custom_total_tax_amount = header["Tax"]
            doc.net_total = header["Total Amount"]
            doc.cheque_no = header["Cheque/Reference No"]
            doc.cheque_date = header["Cheque/Reference Date"]

            # References
            for _, row in group.iterrows():
                custom_tax_code, ap_tax_code = None, None
                if header["DocType"] == 'OR':
                    custom_tax_code = row["Tax Code (Accounting Entries)"]
                else:
                    ap_tax_code = row["Tax Code (Accounting Entries)"]
                
                doc.append("accounts", {
                    "account": row["Account (Accounting Entries)"],
                    "custom_description": row["Description (Accounting Entries)"],
                    "custom_tax_code": custom_tax_code,
                    "ap_tax_code": ap_tax_code,
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
            logger.error(f"❌ Failed to import cashbook {invoice_id}: {e}", exc_info=True)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"🕒 Import completed in {elapsed:.2f} seconds.")

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed cashbooks: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_df.sort_values(["ID", "Account (Accounting Entries)", "Debit (Accounting Entries)", "Credit (Accounting Entries)"])
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "cashbook_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        print("✅ All cashbooks imported successfully.")



# helper function
def normalize_account_format(value: str) -> str:
    """
        Ensure exactly one space before and after the hyphen before 'LCESB'.
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'\s*-\s*LCESB$', ' - LCESB', value.strip())
