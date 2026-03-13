from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from healthcare.setup import data

def execute():
	create_custom_fields(data.get("custom_fields"))
