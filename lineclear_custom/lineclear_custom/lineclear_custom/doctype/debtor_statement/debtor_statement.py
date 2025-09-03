# Copyright (c) 2025, Ku Zheng Yan and contributors
# For license information, please see license.txt

import frappe, time
from frappe.model.document import Document
from lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api import get_settings, create_schedule_events, send_statement, send_overdue

class DebtorStatement(Document):
	def before_save(self):
		settings = get_settings()

		# create schedule events based on settings
		if settings.auto_generate_reminder_on_creation == 1:
			create_schedule_events(self.name)


	def on_submit(self):
		settings = get_settings()

		for file in settings.table_files:
			if file.skip_on_creation == 0:

				# send debtor statement
				if file.file_type == 'Debtor Statement':
					send_statement(self.name, include_payment_details=0)
					time.sleep(0.5)

				# send debtor statement (with details)
				if file.file_type == 'Debtor Statement (With Details)':
					send_statement(self.name, include_payment_details=1)
					time.sleep(0.5)

				# send overdue letter
				if file.file_type == 'Overdue Letter':
					send_overdue(self.name)
					time.sleep(0.5)