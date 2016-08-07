# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import cstr
from frappe import _
from frappe.model.document import Document

class CustomField(Document):
	def autoname(self):
		self.set_fieldname()
		self.name = self.dt + "-" + self.fieldname

	def set_fieldname(self):
		if not self.fieldname:
			if not self.label:
				frappe.throw(_("Label is mandatory"))
			# remove special characters from fieldname
			self.fieldname = filter(lambda x: x.isdigit() or x.isalpha() or '_',
				cstr(self.label).lower().replace(' ','_'))

		# fieldnames should be lowercase
		self.fieldname = self.fieldname.lower()

	def validate(self):
		meta = frappe.get_meta(self.dt)
		fieldnames = [df.fieldname for df in meta.get("fields")]

		if self.insert_after and self.insert_after in fieldnames:
			self.idx = fieldnames.index(self.insert_after) + 1

		if not self.idx:
			self.idx = len(fieldnames) + 1

		self._old_fieldtype = self.db_get('fieldtype')

		if not self.fieldname:
			frappe.throw(_("Fieldname not set for Custom Field"))

	def on_update(self):
		frappe.clear_cache(doctype=self.dt)
		if not self.flags.ignore_validate:
			# validate field
			from frappe.core.doctype.doctype.doctype import validate_fields_for_doctype
			validate_fields_for_doctype(self.dt)

		# update the schema
		if not frappe.db.get_value('DocType', self.dt, 'issingle'):
			if (self.fieldname not in frappe.db.get_table_columns(self.dt)
				or getattr(self, "_old_fieldtype", None) != self.fieldtype):
				from frappe.model.db_schema import updatedb
				updatedb(self.dt)

	def on_trash(self):
		# delete property setter entries
		frappe.db.sql("""\
			DELETE FROM `tabProperty Setter`
			WHERE doc_type = %s
			AND field_name = %s""",
				(self.dt, self.fieldname))

		frappe.clear_cache(doctype=self.dt)

	def validate_insert_after(self, meta):
		if not meta.get_field(self.insert_after):
			frappe.throw(_("Insert After field '{0}' mentioned in Custom Field '{1}', with label '{2}', does not exist")
				.format(self.insert_after, self.name, self.label), frappe.DoesNotExistError)

		if self.fieldname == self.insert_after:
			frappe.throw(_("Insert After cannot be set as {0}").format(meta.get_label(self.insert_after)))

@frappe.whitelist()
def get_fields_label(doctype=None):
	return [{"value": df.fieldname or "", "label": _(df.label or "")} for df in frappe.get_meta(doctype).get("fields")]

def create_custom_field_if_values_exist(doctype, df):
	df = frappe._dict(df)
	if df.fieldname in frappe.db.get_table_columns(doctype) and \
		frappe.db.sql("""select count(*) from `tab{doctype}`
			where ifnull({fieldname},'')!=''""".format(doctype=doctype, fieldname=df.fieldname))[0][0]:

		create_custom_field(doctype, df)


def create_custom_field(doctype, df):
	df = frappe._dict(df)
	if not frappe.db.get_value("Custom Field", {"dt": doctype, "fieldname": df.fieldname}):
		frappe.get_doc({
			"doctype":"Custom Field",
			"dt": doctype,
			"permlevel": df.permlevel or 0,
			"label": df.label,
			"fieldname": df.fieldname or df.label.lower().replace(' ', '_'),
			"fieldtype": df.fieldtype,
			"options": df.options,
			"insert_after": df.insert_after,
			"print_hide": df.print_hide
		}).insert()
