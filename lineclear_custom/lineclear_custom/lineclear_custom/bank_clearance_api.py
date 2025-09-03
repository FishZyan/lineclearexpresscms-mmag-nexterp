import frappe, io, xlsxwriter, os
from frappe.utils import formatdate,getdate

@frappe.whitelist()
def update_clearance_date(bank_account, from_date, to_date):
	bank_transactions = get_bank_transactions(bank_account)

	synced_count, failed_count = 0, 0
	failed_entries = []

	for transaction in bank_transactions:
		transaction.payment_entries = []
		linked_payments = frappe.db.get_all('Bank Transaction Payments',
			filters={"parent": transaction.name},
			fields=['payment_document', 'payment_entry']
		)
		
		if not linked_payments:
			continue

		transaction.payment_entries.extend(linked_payments)

		for entry in linked_payments:
			try:
				doctype = entry.payment_document
				docname = entry.payment_entry
				clearance_date = transaction.date

				if doctype == "Sales Invoice":
					frappe.db.set_value(
						"Sales Invoice Payment",
						dict(parenttype=doctype, parent=docname),
						"clearance_date",
						clearance_date,
					)
				else:
					frappe.db.set_value(doctype, docname, "clearance_date", clearance_date)
				synced_count += 1
			except Exception as e:
				failed_entries.append(transaction)
				failed_count += 1

	if failed_entries:
		file_url = export_failed_transactions(failed_entries)
	else:
		file_url = None
	
	summary = {
		"synced": synced_count,
		"failed": failed_count,
		"file_url": file_url
	}
	return summary


def get_bank_transactions(bank_account, from_date=None, to_date=None):
	# returns bank transactions for a bank account
	filters = []
	filters.append(["bank_account", "=", bank_account])
	filters.append(["docstatus", "=", 1])
	filters.append(["status", "=", 'Reconciled'])
	if to_date:
		filters.append(["date", "<=", to_date])
	if from_date:
		filters.append(["date", ">=", from_date])
	transactions = frappe.get_all(
		"Bank Transaction",
		fields=[
			"date",
			"deposit",
			"withdrawal",
			"currency",
			"description",
			"name",
			"bank_account",
			"company",
			"unallocated_amount",
			"reference_number",
			"party_type",
			"party",
		],
		filters=filters,
		order_by="date",
	)
	return transactions


def export_failed_transactions(failed_entries):
	headers = [
		"date",
		"deposit",
		"withdrawal",
		"currency",
		"description",
		"name",
		"bank_account"
	]

	output = io.BytesIO()
	workbook = xlsxwriter.Workbook(output, {'in_memory': True})
	worksheet = workbook.add_worksheet('Sheet 1')

	# write headers
	header_format = workbook.add_format({'bold': True, 'bg_color': '#D9EAD3', 'border': 1, 'align': 'center', 'valign': 'vcenter'})
	for col, header in enumerate(headers):
		worksheet.write(0, col, header, header_format)

	if failed_entries:
		# write data rows dynamically based on field_names
		for row_idx, row in enumerate(failed_entries, start=1):
			for col_idx, field in enumerate(headers):
				value = getattr(row, field, "")
				if "date" in field and value:
					value = formatdate(value, "yyyy-mm-dd")
				worksheet.write(row_idx, col_idx, value)

	workbook.close()
	output.seek(0)

	# send the Excel file as response
	filename =  f"bank_clearance_error_{getdate().strftime("%Y-%m-%d")}.xlsx"
	file_doc = frappe.get_doc({
		"doctype": "File",
		"file_name": filename,
		"is_private": 0,  # or 1 if you want to restrict access
		"content": output.read(),
		"attached_to_doctype": None,
		"attached_to_name": None
	}).insert(ignore_permissions=True)

	return file_doc.file_url