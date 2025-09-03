import pandas as pd
import frappe, os, time


def update_apinvoice():
    # filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "source", "apinvoice_20250331.xlsx")
    filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apinvoice_error_fixed.xlsx")
    source_df = pd.read_excel(filepath)
    source_df.fillna('', inplace=True)

    start_time = time.time()
    logger = frappe.logger("apinvoice_patch")
    
    count, updated, skipped = 0, 0, 0
    length = len(source_df["ID"].unique())
    failed_docs, failed_rows = [], []
    doctype = 'Purchase Invoice Item'

    grouped = source_df.groupby('ID')

    for invoice_id, group in grouped:
        try:
            items = frappe.get_all(doctype, filters={'parent': invoice_id}, fields=['name'], order_by='idx asc')

            if len(group) != len(items):
                logger.warning(f"⚠️ Row mismatch in {invoice_id}: Excel rows ({len(group)}) ≠ Items ({len(items)})")
                failed_docs.append(invoice_id)
                failed_rows.append(group.copy())
                skipped += len(group)
                continue
            
            index = 0

            for _, row in group.iterrows():
                item_name = items[index]['name']
                item_doc = frappe.get_doc('Purchase Invoice Item', item_name)
                item_doc.custom_tax_code = row["Tax Code (Items)"]
                item_doc.custom_tax_amount = max(0, row["Tax Amount (Items)"])
                item_doc.save(ignore_permissions=True)
                updated += 1
                index += 1
                # print(row.to_dict())
                # print(item_doc.as_dict())
            
            frappe.db.commit()
            count += 1
            print(f"Progressing...{count}/{length}")

        except Exception as e:
            logger.error(f"❌ Failed to update invoice {invoice_id}: {e}", exc_info=True)
            failed_docs.append(invoice_id)
            failed_rows.append(group.copy())
            skipped += len(group)
        
        # break

    end_time = time.time()
    elapsed = end_time - start_time

    if failed_docs:
        print(f"⚠️ Import completed with errors. Failed invoices: {failed_docs}")
        failed_df = pd.concat(failed_rows)
        failed_filepath = os.path.join(frappe.get_app_path("lineclear_custom"), "lineclear_custom", "apinvoice_patch_error.xlsx")
        failed_df.to_excel(failed_filepath, index=False)
    else:
        logger.info(f"✅ Done in {elapsed:.2f} seconds. Updated: {updated}, Skipped: {skipped}")
        print(f"\n✅ Done in {elapsed:.2f} seconds. Updated: {updated}, Skipped: {skipped}")