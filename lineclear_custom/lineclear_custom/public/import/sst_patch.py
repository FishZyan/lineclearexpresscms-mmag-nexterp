import pandas as pd
import frappe, os, time


def update_invoice():
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "invoice_cleared_2024.csv")
    # source_df = pd.read_csv(filepath)

    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "sst-patch.xlsx")
    source_df = pd.read_excel(filepath)
    source_df.fillna('', inplace=True)

    start_time = time.time()
    logger = frappe.logger("sst_patch")
    
    count = 0
    length = len(source_df["ID"].unique())

    failed_docs, failed_rows = [], []
    doctype = 'Sales Invoice'

    grouped = source_df.groupby('ID')
    for invoice_id, group in grouped:
        try:
            # patch invoice with \t in name
            # invoice_id = invoice_id.strip() + '	A'

            doc = frappe.get_doc(doctype, invoice_id)

            if not doc:
                continue

            header = group.iloc[0]
            print('doc_no:', invoice_id, 'knockoff_date:', header["Knock Off Date"])
            doc.knock_off_date = header["Knock Off Date"]
            doc.save()

            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{length}")

        except Exception as e:
            logger.error(f"❌ Failed to update invoice {invoice_id}: {e}", exc_info=True)
            failed_docs.append(invoice_id)
            failed_rows.append(group.copy())

    end_time = time.time()
    elapsed = end_time - start_time

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed invoices: {failed_docs}")
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "invoice_patch_error.xlsx")
        
        if os.path.exists(failed_filepath):
            failed_df = pd.read_excel(failed_filepath)
            new_df = pd.concat(failed_rows, ignore_index=True)
            failed_df = pd.concat([failed_df, new_df], ignore_index=True)
        else:
            failed_df = pd.concat(failed_rows)

        failed_df.to_excel(failed_filepath, index=False)
    else:
        logger.info(f"✅ Done in {elapsed:.2f} seconds.")
        print(f"\n✅ Done in {elapsed:.2f} seconds.")




def update_debit():
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "sst_cleared", "debit_cleared.csv")
    source_df = pd.read_csv(filepath)
    source_df.fillna('', inplace=True)

    start_time = time.time()
    logger = frappe.logger("sst_patch")
    
    count = 0
    length = len(source_df["ID"].unique())

    failed_docs, failed_rows = [], []
    doctype = 'Journal Entry'

    grouped = source_df.groupby('ID')
    for invoice_id, group in grouped:
        try:
            doc = frappe.get_doc(doctype, invoice_id)
            header = group.iloc[0]
            doc.knock_off_date = header["Knock Off Date"]
            doc.save()

            frappe.db.commit()
            count += 1
            print("ID:", doc.name)
            print(f"Progressing...{count}/{length}")

        except Exception as e:
            logger.error(f"❌ Failed to update debit {invoice_id}: {e}", exc_info=True)
            failed_docs.append(invoice_id)
            failed_rows.append(group.copy())

    end_time = time.time()
    elapsed = end_time - start_time

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed debit notes: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "debit_patch_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        logger.info(f"✅ Done in {elapsed:.2f} seconds.")
        print(f"\n✅ Done in {elapsed:.2f} seconds.")