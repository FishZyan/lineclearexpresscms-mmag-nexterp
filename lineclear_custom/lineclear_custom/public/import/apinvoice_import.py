import pandas as pd
import numpy as np
import frappe, os, time, re
from frappe.utils import flt, getdate

"""
Things-to-do before import:
1. 201-1020 - WORK IN PROGRESS - RENOVATION - LCESB | is_group - 0
2. 201-1006 - WORK IN PROGRESS - FIXED ASSETS - LCESB | is_group - 0
3. 420-0000 - HIRE PURCHASE CREDITOR - LCESB | Account Type - Payable
4. 420-1000 - HIRE PURCHASE INTEREST SUSPENSE - LCESB | Account Type - Payable
5. 610-0018 - COST - INSPECTION FOR MOTOR VEHICLES - LCESB | Account Type - Payable

6. Enable Negative Item Rate @ Selling Settings
"""

def import_apinvoice():
    start_time = time.time()
    logger = frappe.logger("apinvoice_import")
    failed_docs, failed_rows = [], []

    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "source", "apinvoice_20250331.xlsx")
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apinvoice_error_fixed.xlsx")
    source_df = pd.read_excel(filepath)

    source_df.fillna('', inplace=True)

    grouped = source_df.groupby("ID")

    count = 0
    doctype = "Purchase Invoice"
    length = len(source_df["ID"].unique())

    for invoice_id, group in grouped:

        try:
            header = group.iloc[0]
            doc = frappe.new_doc(doctype)
            doc.name = header["ID"]
            doc.set_posting_time = 1
            doc.docstatus = 1
            doc.posting_date = header["Date"]
            doc.due_date = header["Due Date"]
            doc.supplier = header["Supplier"]
            doc.supplier_name = header["Supplier Name"]
            doc.bill_no = header["Supplier Invoice No"]
            doc.bill_date = header["Supplier Invoice Date"]
            doc.currency = header["Currency"]
            doc.total = header["Total"]
            doc.base_total = header["Total (Company Currency)"]
            doc.net_total = header["Net Total"]
            doc.base_net_total = header["Net Total (Company Currency)"]
            doc.paid_amount = header["Paid Amount"]
            doc.base_paid_amount = header["Paid Amount (Company Currency)"]
            doc.oustanding_amount = header["Outstanding Amount"]
            doc.company = header["Company"]
            doc.credit_to = header["Credit To"]
            doc.disable_rounded_total = header["Disable Rounded Total"]
            
            # Items
            for _, row in group.iterrows():
                doc.append("items", {
                    "qty": max(0, flt(row["Accepted Qty (Items)"])),
                    "stock_qty": max(0, flt(row["Accepted Qty in Stock UOM (Items)"])),
                    "amount": flt(row["Amount (Items)"]),
                    "base_amount": flt(row["Amount (Company Currency) (Items)"]),
                    "description": row["Description (Items)"],
                    "expense_account": normalize_account_format(row["Expense Head (Items)"]),
                    "item_name": row["Item Name (Items)"],
                    "net_rate": flt(row["Net Rate (Items)"]),
                    "base_net_rate": flt(row["Net Rate (Company Currency) (Items)"]),
                    "net_amount": flt(row["Net Amount (Items)"]),
                    "base_net_amount": flt(row["Net Amount (Company Currency) (Items)"]),
                    "rate": flt(row["Rate (Items)"]),
                    "base_rate": flt(row["Rate (Company Currency) (Items)"]),
                    "uom": row["UOM (Items)"],
                    "conversion_factor": flt(row["UOM Conversion Factor (Items)"]),
                    "custom_tax_code": row["Tax Code (Items)"],
                    "custom_tax_amount": row["Tax Amount (Items)"],
                    "cost_center": row["Cost Center (Items)"] or "Main - LCESB"
                })

            # Taxes
            for _, tax_row in group.iterrows():
                account_head = tax_row.get("Account Head (Purchase Taxes and Charges)", "").strip()
                if not account_head:
                    continue

                # if not pd.isna(tax_row["Account Head (Purchase Taxes and Charges)"]):
                doc.append("taxes", {
                    "account_head": tax_row["Account Head (Purchase Taxes and Charges)"],
                    "add_deduct_tax": tax_row["Add or Deduct (Purchase Taxes and Charges)"],
                    "tax_amount": flt(tax_row["Amount (Purchase Taxes and Charges)"]),
                    "base_tax_amount": flt(tax_row["Amount (Company Currency) (Purchase Taxes and Charges)"]),
                    "category": tax_row["Consider Tax or Charge for (Purchase Taxes and Charges)"],
                    "included_in_paid_amount": tax_row["Considered In Paid Amount (Purchase Taxes and Charges)"],
                    "description": tax_row["Description (Purchase Taxes and Charges)"],
                    "charge_type": tax_row["Type (Purchase Taxes and Charges)"],
                    "rate": flt(tax_row["Tax Rate (Purchase Taxes and Charges)"]),
                    "total": flt(tax_row["Total (Purchase Taxes and Charges)"]),
                    "base_total": flt(tax_row["Total (Company Currency) (Purchase Taxes and Charges)"]),
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
            logger.error(f"❌ Failed to import invoice {invoice_id}: {e}", exc_info=True)

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"🕒 Import completed in {elapsed:.2f} seconds.")

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed invoices: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apinvoice_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        print("✅ All invoices imported successfully.")



# helper function
def normalize_account_format(value: str) -> str:
    """
        Ensure exactly one space before and after the hyphen before 'LCESB'.
    """
    if not isinstance(value, str):
        value = str(value)
    return re.sub(r'\s*-\s*LCESB$', ' - LCESB', value.strip())
