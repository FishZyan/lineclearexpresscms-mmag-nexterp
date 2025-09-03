import pandas as pd
import frappe, os, time


def update_apcredit():
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_patch.xlsx")
    source_df = pd.read_excel(filepath)
    source_df.fillna('', inplace=True)

    start_time = time.time()
    logger = frappe.logger("apcredit_patch")

    count = 0
    skipped = 0
    length = len(source_df["ID"].unique())
    failed_docs, failed_rows = [], []
    doctype = 'Journal Entry'

    grouped = source_df.groupby('ID')

    for invoice_id, group in grouped:
        try:
            # Ensure one value per group
            net_total = group["Net Total"].iloc[0]

            doc = frappe.get_doc(doctype, invoice_id)
            doc.net_total = net_total
            doc.save(ignore_permissions=True)
            frappe.db.commit()

            count += 1
            print(f"Progressing...{count}/{length}")

        except Exception as e:
            logger.error(f"❌ Failed to update note {invoice_id}: {e}", exc_info=True)
            failed_docs.append(invoice_id)
            failed_rows.append(group.copy())
            skipped += len(group)

    end_time = time.time()
    elapsed = end_time - start_time

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed notes: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apcredit_patch_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        print(f"\n✅ Done in {elapsed:.2f} seconds.")