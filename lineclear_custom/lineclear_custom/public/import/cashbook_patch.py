import pandas as pd
import frappe, os, time


def update_cashbook():
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "source", "cashbook_20250331.xlsx")
    source_df = pd.read_excel(filepath)
    source_df.fillna('', inplace=True)

    start_time = time.time()
    logger = frappe.logger("cashbook_patch")
    
    count = 0
    length = len(source_df["ID"].unique())

    failed_docs, failed_rows = [], []
    doctype = 'Journal Entry'

    grouped = source_df.groupby('ID')
    for journal_id, group in grouped:
        try:
            doc = frappe.get_doc(doctype, journal_id)
            header = group.iloc[0]
            doc.accounting_type = header["AccountingType"]
            doc.save()

            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{length}")

        except Exception as e:
            logger.error(f"❌ Failed to update cashbooks {journal_id}: {e}", exc_info=True)
            failed_docs.append(journal_id)
            failed_rows.append(group.copy())

    end_time = time.time()
    elapsed = end_time - start_time

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed cashbooks: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "cashbook_patch_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        logger.info(f"✅ Done in {elapsed:.2f} seconds.")
        print(f"\n✅ Done in {elapsed:.2f} seconds.")