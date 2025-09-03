app_name = "lineclear_custom"
app_title = "LineClear Custom"
app_publisher = "Ku Zheng Yan"
app_description = "Application Customize for Line Clear"
app_email = "helloyan27@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lineclear_custom",
# 		"logo": "/assets/lineclear_custom/logo.png",
# 		"title": "LineClear Custom",
# 		"route": "/lineclear_custom",
# 		"has_permission": "lineclear_custom.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lineclear_custom/css/lineclear_custom.css"
# app_include_js = "/assets/lineclear_custom/js/myinvois_sales_invoice_consolidate.js?v=1.0.3"

# include js, css files in header of web template
# web_include_css = "/assets/lineclear_custom/css/lineclear_custom.css"
# web_include_js = "/assets/lineclear_custom/js/lineclear_custom.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lineclear_custom/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "lineclear_custom/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "lineclear_custom.utils.jinja_methods",
# 	"filters": "lineclear_custom.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "lineclear_custom.install.before_install"
# after_install = "lineclear_custom.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "lineclear_custom.uninstall.before_uninstall"
# after_uninstall = "lineclear_custom.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lineclear_custom.utils.before_app_install"
# after_app_install = "lineclear_custom.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lineclear_custom.utils.before_app_uninstall"
# after_app_uninstall = "lineclear_custom.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lineclear_custom.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lineclear_custom.tasks.all"
# 	],
# 	"daily": [
# 		"lineclear_custom.tasks.daily"
# 	],
# 	"hourly": [
# 		"lineclear_custom.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lineclear_custom.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lineclear_custom.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lineclear_custom.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lineclear_custom.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lineclear_custom.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lineclear_custom.utils.before_request"]
# after_request = ["lineclear_custom.utils.after_request"]

# Job Events
# ----------
# before_job = ["lineclear_custom.utils.before_job"]
# after_job = ["lineclear_custom.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"lineclear_custom.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
    # 'fixtures/sales_taxes_and_charges_template.json',
    {
        "doctype": "Custom Field",
        "filters": [["module", "in", ["LineClear Custom"]]]
    },
    {
        "doctype": "Client Script",
        "filters": [["module", "in", ["LineClear Custom"]]]
    },
    {
        "dt": "Letter Head",
        "filters": [["name", "=", "Line Clear Express Sdn Bhd"]]
    },
    {
        "doctype": "Print Format",
        "filters": [["module", "in", ["LineClear Custom"]]]
    },
    # {
    #     "dt": "Lhdn Settings"
    # },
    {
        "doctype": "Server Script",
        "filters": [["module", "in", ["LineClear Custom"]]]
    },
    {
        "doctype": "Property Setter",
        "filters": [["module", "in", ["LineClear Custom"]]]
    }
]

override_doctype_class = {
	"Journal Entry": "lineclear_custom.lineclear_custom.journal_entry_cancel.CancelInvoice",
    "Purchase Invoice": "lineclear_custom.lineclear_custom.purchase_invoice_cancel.CancelInvoice"
}

doctype_js = { 
    "Bank Clearance": "/public/js/bank_clearance.js",
    "Journal Entry": "/public/js/journal_entry.js",
    "Purchase Invoice": "/public/js/purchase_invoice.js",
    "Payment Entry": "/public/js/payment_entry.js",
    "Sales Invoice": "/public/js/sales_invoice.js",
    # "Sales Invoice": "public/js/myinvois_sales_invoice_consolidate.js"
}

doctype_list_js = {
    "Debtor Statement": "/public/js/debtor_statement_list.js",
    "Journal Entry": "/public/js/journal_entry_list.js",
    "Sales Invoice": "/public/js/sales_invoice_list.js",
    "LHDN Log": "/public/js/get_lhdn_log.js"
}

scheduler_events = {
    # "hourly": [
    #     "lineclear_custom.autocount_import.import_to_erp"
    # ],
    # "cron": {
    #     "35 09 * * *": ["lineclear_custom.lineclear_custom.doctype.debtor_statement.debtor_statement_api.schedule_notifications"]
    # }
}