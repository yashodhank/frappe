# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals

import frappe, json, os
from frappe import _
import frappe.permissions
import re
from frappe.utils.csvutils import UnicodeWriter
from frappe.utils import cstr, cint, flt, formatdate, format_datetime
from  frappe.core.page.data_import_tool.data_import_tool import get_data_keys

reflags = {
	"I":re.I,
	"L":re.L,
	"M":re.M,
	"U":re.U,
	"S":re.S,
	"X":re.X,
	"D": re.DEBUG
}

@frappe.whitelist()
def get_template(doctype=None, parent_doctype=None, all_doctypes="No", with_data="No"):
	all_doctypes = all_doctypes=="Yes"
	docs_to_export = {}
	if doctype:
		if isinstance(doctype, basestring):
			doctype = [doctype];
		if len(doctype) > 1:
			docs_to_export = doctype[1]
		doctype = doctype[0]

	if not parent_doctype:
		parent_doctype = doctype

	column_start_end = {}

	if all_doctypes:
		doctype_parentfield = {}
		child_doctypes = []
		for df in frappe.get_meta(doctype).get_table_fields():
			child_doctypes.append(df.options)
			doctype_parentfield[df.options] = df.fieldname

	def get_data_keys_definition():
		return get_data_keys()

	def add_main_header():
		w.writerow([_('Data Import Template')])
		w.writerow([get_data_keys_definition().main_table, doctype])

		if parent_doctype != doctype:
			w.writerow([get_data_keys_definition().parent_table, parent_doctype])
		else:
			w.writerow([''])

		w.writerow([''])
		w.writerow([_('Notes:')])
		w.writerow([_('Please do not change the template headings.')])
		w.writerow([_('First data column must be blank.')])
		w.writerow([_('If you are uploading new records, leave the "name" (ID) column blank.')])
		w.writerow([_('If you are uploading new records, "Naming Series" becomes mandatory, if present.')])
		w.writerow([_('Only mandatory fields are necessary for new records. You can delete non-mandatory columns if you wish.')])
		w.writerow([_('For updating, you can update only selective columns.')])
		w.writerow([_('You can only upload upto 5000 records in one go. (may be less in some cases)')])
		if key == "parent":
			w.writerow([_('"Parent" signifies the parent table in which this row must be added')])
			w.writerow([_('If you are updating, please select "Overwrite" else existing rows will not be deleted.')])

	def build_field_columns(dt):
		meta = frappe.get_meta(dt)

		tablecolumns = filter(None,
			[(meta.get_field(f[0]) or None) for f in frappe.db.sql('desc `tab%s`' % dt)])

		tablecolumns.sort(lambda a, b: int(a.idx - b.idx))

		if dt==doctype:
			column_start_end[dt] = frappe._dict({"start": 0})
		else:
			column_start_end[dt] = frappe._dict({"start": len(columns)})

			append_field_column(frappe._dict({
				"fieldname": "name",
				"label": "ID",
				"fieldtype": "Data",
				"reqd": 1,
				"idx": 0,
				"info": _("Leave blank for new records")
			}), True)

		for docfield in tablecolumns:
			append_field_column(docfield, True)

		# all non mandatory fields
		for docfield in tablecolumns:
			append_field_column(docfield, False)

		# append DocType name
		tablerow[column_start_end[dt].start + 1] = dt
		if dt!=doctype:
			tablerow[column_start_end[dt].start + 2] = doctype_parentfield[dt]

		column_start_end[dt].end = len(columns) + 1

	def append_field_column(docfield, mandatory):
		if docfield and ((mandatory and docfield.reqd) or not (mandatory or docfield.reqd)) \
			and (docfield.fieldname not in ('parenttype', 'trash_reason')) and not docfield.hidden:
			tablerow.append("")
			fieldrow.append(docfield.fieldname)
			labelrow.append(_(docfield.label))
			mandatoryrow.append(docfield.reqd and 'Yes' or 'No')
			typerow.append(docfield.fieldtype)
			inforow.append(getinforow(docfield))
			columns.append(docfield.fieldname)

	def append_empty_field_column():
		tablerow.append("~")
		fieldrow.append("~")
		labelrow.append("")
		mandatoryrow.append("")
		typerow.append("")
		inforow.append("")
		columns.append("")

	def getinforow(docfield):
		"""make info comment for options, links etc."""
		if docfield.fieldtype == 'Select':
			if not docfield.options:
				return ''
			else:
				return _("One of") + ': %s' % ', '.join(filter(None, docfield.options.split('\n')))
		elif docfield.fieldtype == 'Link':
			return 'Valid %s' % docfield.options
		elif docfield.fieldtype == 'Int':
			return 'Integer'
		elif docfield.fieldtype == "Check":
			return "0 or 1"
		elif hasattr(docfield, "info"):
			return docfield.info
		else:
			return ''

	def add_field_headings():
		w.writerow(tablerow)
		w.writerow(labelrow)
		w.writerow(fieldrow)
		w.writerow(mandatoryrow)
		w.writerow(typerow)
		w.writerow(inforow)
		w.writerow([get_data_keys_definition().data_separator])

	def add_data():
		def add_data_row(row_group, dt, doc, rowidx):
			d = doc.copy()
			meta = frappe.get_meta(dt)
			if all_doctypes:
				d.name = '"'+ d.name+'"'

			if len(row_group) < rowidx + 1:
				row_group.append([""] * (len(columns) + 1))
			row = row_group[rowidx]
			for i, c in enumerate(columns[column_start_end[dt].start:column_start_end[dt].end]):
				df = meta.get_field(c)
				fieldtype = df.fieldtype if df else "Data"
				value = d.get(c, "")
				if value:
					if fieldtype == "Date":
						value = formatdate(value)
					elif fieldtype == "Datetime":
						value = format_datetime(value)

				row[column_start_end[dt].start + i + 1] = value

		if with_data=='Yes':
			frappe.permissions.can_export(parent_doctype, raise_exception=True)

			# sort nested set doctypes by `lft asc`
			order_by = None
			table_columns = frappe.db.get_table_columns(parent_doctype)
			if 'lft' in table_columns and 'rgt' in table_columns:
				order_by = '`tab{doctype}`.`lft` asc'.format(doctype=parent_doctype)

			# get permitted data only
			data = frappe.get_list(doctype, fields=["*"], limit_page_length=None, order_by=order_by)

			for doc in data:
				op = docs_to_export.get("op")
				names = docs_to_export.get("name")

				if names and op:
					if op == '=' and doc.name not in names:
						continue
					elif op == '!=' and doc.name in names:
						continue
				elif names:
					try:
						sflags = docs_to_export.get("flags", "I,U").upper()
						flags = 0
						for a in re.split('\W+',sflags):
							flags = flags | reflags.get(a,0)

						c = re.compile(names, flags)
						m = c.match(doc.name)
						if not m:
							continue
					except:
						if doc.name not in names:
							continue
				# add main table
				row_group = []

				add_data_row(row_group, doctype, doc, 0)

				if all_doctypes:
					# add child tables
					for child_doctype in child_doctypes:
						for ci, child in enumerate(frappe.db.sql("""select * from `tab%s`
							where parent=%s order by idx""" % (child_doctype, "%s"), doc.name, as_dict=1)):
							add_data_row(row_group, child_doctype, child, ci)

				for row in row_group:
					w.writerow(row)

	w = UnicodeWriter()
	key = 'parent' if parent_doctype != doctype else 'name'

	add_main_header()

	w.writerow([''])
	tablerow = [get_data_keys_definition().doctype, ""]
	labelrow = [_("Column Labels:"), "ID"]
	fieldrow = [get_data_keys_definition().columns, key]
	mandatoryrow = [_("Mandatory:"), _("Yes")]
	typerow = [_('Type:'), 'Data (text)']
	inforow = [_('Info:'), '']
	columns = [key]

	build_field_columns(doctype)
	if all_doctypes:
		for d in child_doctypes:
			append_empty_field_column()
			build_field_columns(d)

	add_field_headings()
	add_data()

	# write out response as a type csv
	frappe.response['result'] = cstr(w.getvalue())
	frappe.response['type'] = 'csv'
	frappe.response['doctype'] = doctype
