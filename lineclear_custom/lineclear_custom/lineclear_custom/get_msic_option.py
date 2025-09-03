import frappe

@frappe.whitelist()
def get_industrial_classification_options(doctype, txt, searchfield, start, page_len, filters):
    if len(txt) > 0:
        return frappe.db.sql("""
                SELECT ic.name, CONCAT(ic.name, ' - ', ic.description)
                FROM `tabIndustrial Classification` ic
                WHERE (ic.name LIKE %(txt)s OR ic.description LIKE %(txt)s)
                ORDER BY ic.name
                LIMIT %(start)s, %(page_len)s
            """, {
                'txt': f"%{txt}%",
                'start': start,
                'page_len': page_len
            })
    return frappe.db.sql("""
                SELECT ic.name, CONCAT(ic.name, ' - ', ic.description)
                FROM `tabIndustrial Classification` ic
                ORDER BY ic.name
                LIMIT %(start)s, %(page_len)s
            """, {
                'start': start,
                'page_len': page_len
            })