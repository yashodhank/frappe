# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import frappe
from frappe.desk.notifications import delete_notification_count_for
from frappe.core.doctype.user.user import STANDARD_USERS
from frappe.utils import cint

@frappe.whitelist()
def get_list(arg=None):
	"""get list of messages"""
	frappe.form_dict['limit_start'] = int(frappe.form_dict['limit_start'])
	frappe.form_dict['limit_page_length'] = int(frappe.form_dict['limit_page_length'])
	frappe.form_dict['user'] = frappe.session['user']

	# set all messages as read
	frappe.db.begin()
	frappe.db.sql("""UPDATE `tabCommunication` set seen = 1
		where
			communication_type in ('Chat', 'Notification')
			and seen = 0
			and reference_doctype = 'User'
			and reference_name = %s""", frappe.session.user)

	delete_notification_count_for("Chat")

	frappe.local.flags.commit = True

	if frappe.form_dict.contact == 'Bot':
		return frappe.db.sql("""select * from `tabCommunication`
			where
				comment_type = 'Bot'
				and reference_doctype = 'User'
				and reference_name = %(user)s
			order by creation desc
			limit %(limit_start)s, %(limit_page_length)s""", frappe.local.form_dict, as_dict=1)

	if frappe.form_dict.contact == frappe.session.user:
		# return messages
		return frappe.db.sql("""select * from `tabCommunication`
			where
				communication_type in ('Chat', 'Notification')
				and comment_type != 'Bot'
				and reference_doctype ='User'
				and (owner=%(contact)s
					or reference_name=%(user)s
					or owner=reference_name)
			order by creation desc
			limit %(limit_start)s, %(limit_page_length)s""", frappe.local.form_dict, as_dict=1)
	else:
		return frappe.db.sql("""select * from `tabCommunication`
			where
				communication_type in ('Chat', 'Notification')
				and reference_doctype ='User'
				and ((owner=%(contact)s and reference_name=%(user)s)
					or (owner=%(contact)s and reference_name=%(contact)s))
			order by creation desc
			limit %(limit_start)s, %(limit_page_length)s""", frappe.local.form_dict, as_dict=1)

@frappe.whitelist()
def get_active_users():
	data = frappe.db.sql("""select name,
		(select count(*) from tabSessions where user=tabUser.name
			and timediff(now(), lastupdate) < time("01:00:00")) as has_session
	 	from tabUser
		where enabled=1 and
		ifnull(user_type, '')!='Website User' and
		name not in ({})
		order by first_name""".format(", ".join(["%s"]*len(STANDARD_USERS))), STANDARD_USERS, as_dict=1)

	# make sure current user is at the top, using has_session = 100
	users = [d.name for d in data]

	if frappe.session.user in users:
		data[users.index(frappe.session.user)]["has_session"] = 100

	else:
		# in case of administrator
		data.append({"name": frappe.session.user, "has_session": 100})

	if 'System Manager' in frappe.get_roles():
		data.append({"name": "Bot", "has_session": 100})

	return data

@frappe.whitelist()
def post(txt, contact, parenttype=None, notify=False, subject=None):
	"""post message"""

	comment_type = None
	if contact == 'Bot':
		contact = frappe.session.user
		comment_type = 'Bot'

	d = frappe.new_doc('Communication')
	d.communication_type = 'Notification' if parenttype else 'Chat'
	d.subject = subject
	d.content = txt
	d.reference_doctype = 'User'
	d.reference_name = contact
	d.sender = frappe.session.user

	if comment_type:
		d.comment_type = comment_type

	d.insert(ignore_permissions=True)

	delete_notification_count_for("Chat")

	if notify and cint(notify):
		_notify(contact, txt, subject)

	return d

@frappe.whitelist()
def delete(arg=None):
	frappe.get_doc("Communication", frappe.form_dict['name']).delete()

def _notify(contact, txt, subject=None):
	from frappe.utils import get_fullname, get_url

	try:
		if not isinstance(contact, list):
			contact = [frappe.db.get_value("User", contact, "email") or contact]
		frappe.sendmail(\
			recipients=contact,
			sender= frappe.db.get_value("User", frappe.session.user, "email"),
			subject=subject or "New Message from " + get_fullname(frappe.session.user),
			message=frappe.get_template("templates/emails/new_message.html").render({
				"from": get_fullname(frappe.session.user),
				"message": txt,
				"link": get_url()
			}))
	except frappe.OutgoingEmailError:
		pass
