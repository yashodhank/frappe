# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
import frappe

@frappe.whitelist()
def get_children():
	doctype = frappe.local.form_dict.get('doctype')
	parent_field = 'parent_' + doctype.lower().replace(' ', '_')
	parent = frappe.form_dict.get("parent") or ""

	return frappe.db.sql("""select name as value,
		is_group as expandable
		from `tab{ctype}`
		where docstatus < 2
		and ifnull(`{parent_field}`,'') = %s
		order by name""".format(ctype=frappe.db.escape(doctype), parent_field=frappe.db.escape(parent_field)),
		parent, as_dict=1)

@frappe.whitelist()
def add_node():
	doctype = frappe.form_dict.get('doctype')
	parent_field = 'parent_' + doctype.lower().replace(' ', '_')
	name_field = doctype.lower().replace(' ', '_') + '_name'

	doc = frappe.new_doc(doctype)
	doc.update({
		name_field: frappe.form_dict['name_field'],
		parent_field: frappe.form_dict['parent'],
		"is_group": frappe.form_dict['is_group']
	})
	if doctype == "Sales Person":
		doc.employee = frappe.form_dict.get('employee')

	doc.save()