import frappe
from frappe.utils import flt, getdate

from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice


class HealthcareSalesInvoice(SalesInvoice):
	def validate(self):
		self.set_missing_insurance_details()
		super().validate()
		self.calculate_patient_insurance_coverage()

	@frappe.whitelist()
	def set_healthcare_services(self, checked_values):
		from erpnext.stock.get_item_details import get_item_details

		for checked_item in checked_values:
			item_line = self.append("items", {})
			price_list, price_list_currency = frappe.db.get_values(
				"Price List", {"selling": 1}, ["name", "currency"]
			)[0]
			args = {
				"doctype": "Sales Invoice",
				"item_code": checked_item.get("item"),
				"company": self.company,
				"customer": frappe.db.get_value("Patient", self.patient, "customer"),
				"selling_price_list": self.selling_price_list or price_list,
				"price_list_currency": self.currency or price_list_currency,
				"plc_conversion_rate": 1.0,
				"conversion_rate": 1.0,
			}
			item_details = get_item_details(args)
			item_line.item_code = checked_item.get("item")
			item_line.qty = 1

			if checked_item.get("qty"):
				item_line.qty = checked_item.get("qty")

			if checked_item.get("rate"):
				item_line.rate = checked_item.get("rate")
			else:
				item_line.rate = item_details.price_list_rate

			if checked_item.get("income_account"):
				item_line.income_account = checked_item.get("income_account")

			if checked_item.get("dt"):
				item_line.reference_dt = checked_item.get("dt")

			if checked_item.get("dn"):
				item_line.reference_dn = checked_item.get("dn")

			if checked_item.get("description"):
				item_line.description = checked_item.get("description")

			if checked_item.get("discount_percentage"):
				item_line.discount_percentage = checked_item.get("discount_percentage", 0)

			if checked_item.get("insurance_coverage"):
				item_line.insurance_coverage = checked_item.get("insurance_coverage")

			if checked_item.get("patient_insurance_policy"):
				item_line.patient_insurance_policy = checked_item.get("patient_insurance_policy")

			if checked_item.get("coverage_percentage"):
				item_line.coverage_percentage = checked_item.get("coverage_percentage", 0)

			if checked_item.get("insurance_payor"):
				item_line.insurance_payor = checked_item.get("insurance_payor")

			if checked_item.get("coverage_rate"):
				item_line.coverage_rate = checked_item.get("coverage_rate", 0)

			if checked_item.get("coverage_qty"):
				item_line.coverage_qty = checked_item.get("coverage_qty", 0)

			if item_line.get("discount_percentage"):
				item_line.discount_amount = flt(item_line.rate) * flt(item_line.discount_percentage, 0) * 0.01
				item_line.rate = flt(item_line.rate) - flt(item_line.discount_amount)

			if checked_item.get("dt") == "Lab Test":
				lab_test = frappe.get_doc("Lab Test", checked_item["dn"])
				item_line.service_unit = lab_test.service_unit
				item_line.practitioner = lab_test.practitioner
				item_line.medical_department = lab_test.department

			item_line.amount = flt(item_line.rate) * flt(item_line.qty)

			if item_line.get("insurance_coverage"):
				item_line.insurance_coverage_amount = (
					flt(item_line.amount) * 0.01 * flt(item_line.get("coverage_percentage", 0))
				)

		super().set_missing_values(for_validate=True)
		self.calculate_patient_insurance_coverage()

	def calculate_patient_insurance_coverage(self):
		total_coverage_amount = 0.0

		if not hasattr(self, "items"):
			return

		for item in self.items:
			if item.amount and item.get("insurance_coverage"):
				item.insurance_coverage_amount = item.amount * 0.01 * flt(item.coverage_percentage)

			if item.insurance_coverage_amount and flt(item.insurance_coverage_amount) > 0:
				total_coverage_amount += flt(item.insurance_coverage_amount)

		self.total_insurance_coverage_amount = total_coverage_amount
		if self.total_insurance_coverage_amount:
			self.patient_payable_amount = self.outstanding_amount - self.total_insurance_coverage_amount
		else:
			self.patient_payable_amount = self.outstanding_amount

	def set_missing_insurance_details(self):
		for item in self.items:
			if not item.insurance_coverage:
				filters = {
					"patient": self.patient,
					"company": self.company,
					"item_code": item.item_code,
					"docstatus": 1,
					"status": ["in", ["Approved", "Partly Invoiced"]],
					"coverage_validity_end_date": [">=", getdate()],
				}
				if item.reference_dt and item.reference_dn:
					filters["template_dt"] = item.reference_dt
					filters["template_dn"] = item.reference_dn

				coverage = frappe.db.get_value(
					"Patient Insurance Coverage",
					filters,
					["name", "coverage", "discount", "price_list_rate", "policy_number", "qty"],
					as_dict=True,
				)
				if coverage:
					item.insurance_coverage = coverage.name
					item.coverage_percentage = coverage.coverage
					item.discount_percentage = coverage.discount
					item.coverage_rate = coverage.price_list_rate
					item.coverage_qty = coverage.qty
					item.patient_insurance_policy = coverage.policy_number

					if not item.rate:
						item.rate = coverage.price_list_rate
