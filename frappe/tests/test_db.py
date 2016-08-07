#  -*- coding: utf-8 -*-

# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# MIT License. See license.txt

from __future__ import unicode_literals
import unittest
import frappe

class TestDB(unittest.TestCase):
	def test_get_value(self):
		self.assertEquals(frappe.db.get_value("User", {"name": ["=", "Administrator"]}), "Administrator")
		self.assertEquals(frappe.db.get_value("User", {"name": ["like", "Admin%"]}), "Administrator")
		self.assertEquals(frappe.db.get_value("User", {"name": ["!=", "Guest"]}), "Administrator")
		self.assertEquals(frappe.db.get_value("User", {"name": ["<", "B"]}), "Administrator")
		self.assertEquals(frappe.db.get_value("User", {"name": ["<=", "Administrator"]}), "Administrator")

		self.assertEquals(frappe.db.sql("""select name from `tabUser` where name > "s" """)[0][0],
			frappe.db.get_value("User", {"name": [">", "s"]}))

		self.assertEquals(frappe.db.sql("""select name from `tabUser` where name >= "t" """)[0][0],
			frappe.db.get_value("User", {"name": [">=", "t"]}))

	def test_escape(self):
		frappe.db.escape("香港濟生堂製藥有限公司 - IT".encode("utf-8"))

	def test_multiple_queries(self):
		# implicit commit
		self.assertRaises(frappe.SQLError, frappe.db.sql, """select name from `tabUser`; truncate `tabEmail Queue`""")
