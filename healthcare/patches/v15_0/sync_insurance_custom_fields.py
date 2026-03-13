import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from healthcare.setup import data

def execute():
	custom_fields = data.get("custom_fields")
	to_install = {}

	for doctype, fields in custom_fields.items():
		if not frappe.db.exists("DocType", doctype):
			continue

		meta = frappe.get_meta(doctype)
		doctype_fields = []
		for field in fields:
			if not meta.has_field(field.get("fieldname")):
				doctype_fields.append(field)

		if doctype_fields:
			to_install[doctype] = doctype_fields

	create_custom_fields(to_install)
