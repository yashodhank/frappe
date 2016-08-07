# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe, json
import frappe.utils
import frappe.share
import frappe.defaults
import frappe.desk.form.meta
from frappe.model.utils.list_settings import get_list_settings
from frappe.permissions import get_doc_permissions
from frappe import _

@frappe.whitelist()
def getdoc(doctype, name, user=None):
	"""
	Loads a doclist for a given document. This method is called directly from the client.
	Requries "doctype", "name" as form variables.
	Will also call the "onload" method on the document.
	"""

	if not (doctype and name):
		raise Exception, 'doctype and name required!'

	if not name:
		name = doctype

	if not frappe.db.exists(doctype, name):
		return []

	try:
		doc = frappe.get_doc(doctype, name)
		run_onload(doc)

		if not doc.has_permission("read"):
			raise frappe.PermissionError, ("read", doctype, name)

		# add file list
		get_docinfo(doc)

	except Exception:
		frappe.errprint(frappe.utils.get_traceback())
		frappe.msgprint(_('Did not load'))
		raise

	if doc and not name.startswith('_'):
		frappe.get_user().update_recent(doctype, name)

	doc.add_seen()

	frappe.response.docs.append(doc)

@frappe.whitelist()
def getdoctype(doctype, with_parent=False, cached_timestamp=None):
	"""load doctype"""

	docs = []
	parent_dt = None

	# with parent (called from report builder)
	if with_parent:
		parent_dt = frappe.model.meta.get_parent_dt(doctype)
		if parent_dt:
			docs = get_meta_bundle(parent_dt)
			frappe.response['parent_dt'] = parent_dt

	if not docs:
		docs = get_meta_bundle(doctype)

	frappe.response['user_permissions'] = get_user_permissions(docs)
	frappe.response['list_settings'] = get_list_settings(parent_dt or doctype)

	if cached_timestamp and docs[0].modified==cached_timestamp:
		return "use_cache"

	frappe.response.docs.extend(docs)

def get_meta_bundle(doctype):
	bundle = [frappe.desk.form.meta.get_meta(doctype)]
	for df in bundle[0].fields:
		if df.fieldtype=="Table":
			bundle.append(frappe.desk.form.meta.get_meta(df.options, not frappe.conf.developer_mode))
	return bundle

@frappe.whitelist()
def get_docinfo(doc=None, doctype=None, name=None):
	if not doc:
		doc = frappe.get_doc(doctype, name)
		if not doc.has_permission("read"):
			raise frappe.PermissionError

	frappe.response["docinfo"] = {
		"attachments": get_attachments(doc.doctype, doc.name),
		"communications": _get_communications(doc.doctype, doc.name),
		"assignments": get_assignments(doc.doctype, doc.name),
		"permissions": get_doc_permissions(doc),
		"shared": frappe.share.get_users(doc.doctype, doc.name,
			fields=["user", "read", "write", "share", "everyone"])
	}

def get_user_permissions(meta):
	out = {}
	all_user_permissions = frappe.defaults.get_user_permissions()

	for m in meta:
		for df in m.get_fields_to_check_permissions(all_user_permissions):
			out[df.options] = list(set(all_user_permissions[df.options]))

	return out

def get_attachments(dt, dn):
	return frappe.get_all("File", fields=["name", "file_name", "file_url", "is_private"],
		filters = {"attached_to_name": dn, "attached_to_doctype": dt})

@frappe.whitelist()
def get_communications(doctype, name, start=0, limit=20):
	doc = frappe.get_doc(doctype, name)
	if not doc.has_permission("read"):
		raise frappe.PermissionError

	return _get_communications(doctype, name, start, limit)


def _get_communications(doctype, name, start=0, limit=20):
	communications = get_communication_data(doctype, name, start, limit)
	for c in communications:
		if c.communication_type=="Communication":
			c.attachments = json.dumps(frappe.get_all("File",
				fields=["file_url", "is_private"],
				filters={"attached_to_doctype": "Communication",
					"attached_to_name": c.name}
				))

		elif c.communication_type=="Comment" and c.comment_type=="Comment":
			c.content = frappe.utils.markdown(c.content)

	return communications

def get_communication_data(doctype, name, start=0, limit=20, after=None, fields=None,
	group_by=None, as_dict=True):
	'''Returns list of communications for a given document'''
	if not fields:
		fields = '''name, communication_type,
			communication_medium, comment_type,
			content, sender, sender_full_name, creation, subject, delivery_status, _liked_by,
			timeline_doctype, timeline_name,
			reference_doctype, reference_name,
			link_doctype, link_name,
			"Communication" as doctype'''

	conditions = '''communication_type in ("Communication", "Comment")
			and (
				(reference_doctype=%(doctype)s and reference_name=%(name)s)
				or (timeline_doctype=%(doctype)s
					and timeline_name=%(name)s
					and communication_type="Comment"
					and comment_type in ("Created", "Updated", "Submitted", "Cancelled", "Deleted"))
			)
			and (comment_type is null or comment_type != 'Update')'''

	if after:
		# find after a particular date
		conditions+= ' and creation > {0}'.format(after)

	communications = frappe.db.sql("""select {fields}
		from tabCommunication
		where {conditions} {group_by}
		order by creation desc limit %(start)s, %(limit)s""".format(
			fields = fields, conditions=conditions, group_by=group_by or ""),
			{ "doctype": doctype, "name": name, "start": frappe.utils.cint(start), "limit": limit },
			as_dict=as_dict)

	return communications

def get_assignments(dt, dn):
	cl = frappe.db.sql("""select owner, description from `tabToDo`
		where reference_type=%(doctype)s and reference_name=%(name)s and status="Open"
		order by modified desc limit 5""", {
			"doctype": dt,
			"name": dn
		}, as_dict=True)

	return cl

@frappe.whitelist()
def get_badge_info(doctypes, filters):
	filters = json.loads(filters)
	doctypes = json.loads(doctypes)
	filters["docstatus"] = ["!=", 2]
	out = {}
	for doctype in doctypes:
		out[doctype] = frappe.db.get_value(doctype, filters, "count(*)")

	return out

def run_onload(doc):
	doc.set("__onload", frappe._dict())
	doc.run_method("onload")
