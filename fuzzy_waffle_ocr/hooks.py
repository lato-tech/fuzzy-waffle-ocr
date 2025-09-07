app_name = "fuzzy_waffle_ocr"
app_title = "Fuzzy Waffle OCR"
app_publisher = "Lato Tech"
app_description = "Intelligent OCR-based invoice processing for ERPNext with learning capabilities"
app_icon = "octicon octicon-file-code"
app_color = "grey"
app_email = "info@namiex.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/fuzzy_waffle_ocr/css/fuzzy_waffle_ocr.css"
# app_include_js = "/assets/fuzzy_waffle_ocr/js/fuzzy_waffle_ocr.js"

# include js, css files in header of web template
# web_include_css = "/assets/fuzzy_waffle_ocr/css/fuzzy_waffle_ocr.css"
# web_include_js = "/assets/fuzzy_waffle_ocr/js/fuzzy_waffle_ocr.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "fuzzy_waffle_ocr/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Purchase Invoice" : "public/js/purchase_invoice.js",
    "Journal Entry" : "public/js/journal_entry.js"
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
#	"methods": "fuzzy_waffle_ocr.utils.jinja_methods",
#	"filters": "fuzzy_waffle_ocr.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "fuzzy_waffle_ocr.install.before_install"
after_install = "fuzzy_waffle_ocr.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "fuzzy_waffle_ocr.uninstall.before_uninstall"
# after_uninstall = "fuzzy_waffle_ocr.uninstall.after_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "fuzzy_waffle_ocr.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
#	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
#	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
#	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Purchase Invoice": {
        "on_update": "fuzzy_waffle_ocr.learning.supplier_learning.update_learning_patterns",
        "after_insert": "fuzzy_waffle_ocr.learning.supplier_learning.record_new_invoice_pattern"
    },
    "Journal Entry": {
        "on_update": "fuzzy_waffle_ocr.learning.journal_learning.update_journal_patterns",
        "after_insert": "fuzzy_waffle_ocr.learning.journal_learning.record_new_journal_pattern"
    }
}

# Scheduled Tasks
# ---------------

scheduler_events = {
    "daily": [
        "fuzzy_waffle_ocr.learning.analytics.calculate_daily_metrics"
    ],
    "weekly": [
        "fuzzy_waffle_ocr.learning.analytics.update_confidence_scores"
    ]
}

# Testing
# -------

# before_tests = "fuzzy_waffle_ocr.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
#	"frappe.desk.doctype.event.event.get_events": "fuzzy_waffle_ocr.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
#	"Task": "fuzzy_waffle_ocr.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# User Data Protection
# --------------------

# user_data_fields = [
#	{
#		"doctype": "{doctype_1}",
#		"filter_by": "{filter_by}",
#		"redact_fields": ["{field_1}", "{field_2}"],
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_2}",
#		"filter_by": "{filter_by}",
#		"partial": 1,
#	},
#	{
#		"doctype": "{doctype_3}",
#		"strict": False,
#	},
#	{
#		"doctype": "{doctype_4}"
#	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
#	"fuzzy_waffle_ocr.auth.validate"
# ]