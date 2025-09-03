import frappe

# bench --site yoursite execute lineclear_custom.patches.patch_file.execute

# def execute():
#     customer()
#     customer_group()
#     journal_entry_item()
#     address()
#     # journal_entry()
#     sales_invoice()
#     sales_invoice_item()

#     remove_custom_fields()
    
#     print("Patch Execution Completed")

def customer():
    # Modify the customer_type field
    doctype = "Customer"

    # Fetch the field definition
    field = frappe.get_doc("DocField", {"parent": doctype, "fieldname": "customer_type"})
    field2 = frappe.get_doc("DocField", {"parent": doctype, "fieldname": "customer_name"})

    # Customer type add new options
    new_options = ['Company', 'Individual', 'Partnership', 'Government']
    field.options = "\n".join(new_options)

    # Customer name make it hidden
    # field2.hidden = 1
    field2.hidden = 0

    # Save the changes
    field.save()
    field2.save()
    frappe.db.commit()

def customer_group():
    # Add new customer groups
    new_customer_groups = [
        "Business_Use",
        "Personal_Use",
        "AGNT_CRDT",
        "AGNT_CASH",
        "AGNT_BOTH",
    ]
    # Ensure all required customer groups exist
    for group_name in new_customer_groups:
        if not frappe.db.exists("Customer Group", group_name):
            doc = frappe.get_doc({
                "doctype": "Customer Group",
                "customer_group_name": group_name
            })
            doc.insert()
    frappe.db.commit()

def address():
    #add new address type
    address_type = frappe.get_doc("DocField", {"parent": "Address", "fieldname": "address_type"})
    address_type_options = ['Billing', 'Pickup', 'Shipping', 'Office', 'Personal', 'Plant', 'Postal', 'Shop', 'Subsidiary', 'Warehouse', 'Current', 'Permanent', 'Other']
    address_type.options = "\n".join(address_type_options)
    address_type.save()
    frappe.db.commit()

def sales_invoice():
    shipping_rule = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "shipping_rule"})
    shipping_rule.hidden = 1
    shipping_rule.save()

    incoterm = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "incoterm"})
    incoterm.hidden = 1
    incoterm.save()

    scan_barcode = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "scan_barcode"})
    scan_barcode.hidden = 1
    scan_barcode.save()

    update_stock = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "update_stock"})
    update_stock.hidden = 1
    update_stock.save()

    tax_category = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "tax_category"})
    tax_category.hidden = 1
    tax_category.save()

    total_qty = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "total_qty"})
    total_qty.hidden = 1
    total_qty.save()

    timesheets = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "timesheets"})
    timesheets.hidden = 1
    timesheets.save()

    apply_discount_on = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "apply_discount_on"})
    apply_discount_on.hidden = 1
    apply_discount_on.save()

    additional_discount_percentage = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "additional_discount_percentage"})
    additional_discount_percentage.hidden = 1
    additional_discount_percentage.save()

    discount_amount = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "discount_amount"})
    discount_amount.hidden = 1
    discount_amount.save()

    is_cash_or_non_trade_discount = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "is_cash_or_non_trade_discount"})
    is_cash_or_non_trade_discount.hidden = 0
    is_cash_or_non_trade_discount.save()

    # currency = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "currency"})
    # currency.hidden = 0
    # currency.save()

    tax_category = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "tax_category"})
    tax_category.hidden = 1
    tax_category.save()

    shipping_rule = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "shipping_rule"})
    shipping_rule.hidden = 1
    shipping_rule.save()

    # incoterm = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "incoterm"})
    # incoterm.hidden = 0
    # incoterm.save()
    
    taxes_and_charges = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "taxes_and_charges"})
    taxes_and_charges.hidden = 0
    taxes_and_charges.save()

    set_posting_time = frappe.get_doc("DocField", {"parent": "Sales Invoice", "fieldname": "set_posting_time"})
    set_posting_time.default = 1
    set_posting_time.hidden = 1
    set_posting_time.save()

    frappe.db.commit()

def sales_invoice_item():
    item_code = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "item_code"})
    item_code.columns = 2
    item_code.save()

    description = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "description"})
    description.in_list_view = 1
    description.columns = 2
    description.save()

    qty = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "qty"})
    qty.columns = 1
    qty.save()

    rate = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "rate"})
    rate.columns = 1
    rate.save()

    item_code = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "item_code"})
    item_code.columns = 1
    item_code.save()

    amount = frappe.get_doc("DocField", {"parent": "Sales Invoice Item", "fieldname": "amount"})
    amount.columns = 1
    amount.save()



    frappe.db.commit()

def journal_entry_item():
    party_type = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "party_type"})
    party_type.hidden = 1
    party_type.save() 

    debit_in_account_currency = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "debit_in_account_currency"})
    debit_in_account_currency.columns = 1
    debit_in_account_currency.save() 

    credit_in_account_currency = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "credit_in_account_currency"})
    credit_in_account_currency.columns = 1
    credit_in_account_currency.save() 

    reference_name = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "reference_name"})
    reference_name.in_list_view = 1
    reference_name.columns = 2
    reference_name.save() 

    reference_type = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "reference_type"})
    reference_type.in_list_view = 1
    reference_type.columns = 1
    reference_type.save() 

    party = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "party"})
    party.columns = 1
    party.save() 

    # from_template = frappe.get_doc("DocField", {"parent": "Journal Entry Account", "fieldname": "from_template"})
    # from_template.hidden = 1
    # from_template.save()

    frappe.db.commit()

def journal_entry():
    naming_series = frappe.get_doc("DocField", {"parent": "Journal Entry", "fieldname": "naming_series"})
    naming_series.hidden = 0
    naming_series.save()

    company = frappe.get_doc("DocField", {"parent": "Journal Entry", "fieldname": "company"})
    company.hidden = 0
    company.save()

    apply_tds = frappe.get_doc("DocField", {"parent": "Journal Entry", "fieldname": "apply_tds"})
    apply_tds.hidden = 0
    apply_tds.save()
    frappe.db.commit()

def remove_custom_fields():
    # Remove custom fields
    sales_invoice_custom_fields = [
        "custom_tax_type",
        "custom_lhdn_tax_type_code",
        "custom_exemption_description",
        "custom_tax_rate",
        "second_tax"
    ]

    custom_field = [
        "Sales Invoice-custom_tax_type",
        "Sales Invoice-custom_lhdn_tax_type_code",
        "Sales Invoice-custom_exemption_description",
        "Sales Invoice-custom_tax_rate",
        "Sales Invoice-custom_second_tax",
        "Journal Entry-custom_sst"
    ]

    # for field in sales_invoice_custom_fields:
    #     if frappe.db.has_column('Sales Invoice', field):
    #         frappe.db.sql(f"ALTER TABLE `tabSales Invoice` DROP COLUMN `{field}`")
    #         frappe.logger().info(f"Removed custom field {field} from Sales Invoice")
    #         print(f"Removed field {field} from Sales Invoice DB")

    for field in custom_field:
        if frappe.db.exists("Custom Field", field):
            frappe.delete_doc("Custom Field", field)
            print(f"Removed custom field {field} from Sales Invoice")