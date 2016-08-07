from __future__ import unicode_literals, absolute_import
import click
import json, os, sys
from distutils.spawn import find_executable
import frappe
from frappe.commands import pass_context, get_site

@click.command('build')
@click.option('--make-copy', is_flag=True, default=False, help='Copy the files instead of symlinking')
@click.option('--verbose', is_flag=True, default=False, help='Verbose')
def build(make_copy=False, verbose=False):
	"Minify + concatenate JS and CSS files, build translations"
	import frappe.build
	import frappe
	frappe.init('')
	frappe.build.bundle(False, make_copy=make_copy, verbose=verbose)

@click.command('watch')
def watch():
	"Watch and concatenate JS and CSS files as and when they change"
	import frappe.build
	frappe.init('')
	frappe.build.watch(True)

@click.command('clear-cache')
@pass_context
def clear_cache(context):
	"Clear cache, doctype cache and defaults"
	import frappe.sessions
	import frappe.website.render
	from frappe.desk.notifications import clear_notifications
	for site in context.sites:
		try:
			frappe.connect(site)
			frappe.clear_cache()
			clear_notifications()
			frappe.website.render.clear_cache()
		finally:
			frappe.destroy()

@click.command('clear-website-cache')
@pass_context
def clear_website_cache(context):
	"Clear website cache"
	import frappe.website.render
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			frappe.website.render.clear_cache()
		finally:
			frappe.destroy()

@click.command('destroy-all-sessions')
@pass_context
def destroy_all_sessions(context):
	"Clear sessions of all users (logs them out)"
	import frappe.sessions
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			frappe.sessions.clear_all_sessions()
			frappe.db.commit()
		finally:
			frappe.destroy()


@click.command('reset-perms')
@pass_context
def reset_perms(context):
	"Reset permissions for all doctypes"
	from frappe.permissions import reset_perms
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			for d in frappe.db.sql_list("""select name from `tabDocType`
				where istable=0 and custom=0"""):
					frappe.clear_cache(doctype=d)
					reset_perms(d)
		finally:
			frappe.destroy()

@click.command('execute')
@click.argument('method')
@click.option('--args')
@click.option('--kwargs')
@pass_context
def execute(context, method, args=None, kwargs=None):
	"Execute a function"
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()

			if args:
				try:
					args = eval(args)
				except NameError:
					args = [args]
			else:
				args = ()

			if kwargs:
				kwargs = eval(kwargs)
			else:
				kwargs = {}

			ret = frappe.get_attr(method)(*args, **kwargs)

			if frappe.db:
				frappe.db.commit()
		finally:
			frappe.destroy()
		if ret:
			print json.dumps(ret)


@click.command('add-to-email-queue')
@click.argument('email-path')
@pass_context
def add_to_email_queue(context, email_path):
	"Add an email to the Email Queue"
	site = get_site(context)

	if os.path.isdir(email_path):
		with frappe.init_site(site):
			frappe.connect()
			for email in os.listdir(email_path):
				with open(os.path.join(email_path, email)) as email_data:
					kwargs = json.load(email_data)
					kwargs['delayed'] = True
					frappe.sendmail(**kwargs)
					frappe.db.commit()


@click.command('export-doc')
@click.argument('doctype')
@click.argument('docname')
@pass_context
def export_doc(context, doctype, docname):
	"Export a single document to csv"
	import frappe.modules
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			frappe.modules.export_doc(doctype, docname)
		finally:
			frappe.destroy()

@click.command('export-json')
@click.argument('doctype')
@click.argument('path')
@click.option('--name', help='Export only one document')
@pass_context
def export_json(context, doctype, path, name=None):
	"Export doclist as json to the given path, use '-' as name for Singles."
	from frappe.core.page.data_import_tool import data_import_tool
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			data_import_tool.export_json(doctype, path, name=name)
		finally:
			frappe.destroy()

@click.command('export-csv')
@click.argument('doctype')
@click.argument('path')
@pass_context
def export_csv(context, doctype, path):
	"Export data import template for DocType"
	from frappe.core.page.data_import_tool import data_import_tool
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			data_import_tool.export_csv(doctype, path)
		finally:
			frappe.destroy()

@click.command('export-fixtures')
@pass_context
def export_fixtures(context):
	"Export fixtures"
	from frappe.utils.fixtures import export_fixtures
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			export_fixtures()
		finally:
			frappe.destroy()

@click.command('import-doc')
@click.argument('path')
@pass_context
def import_doc(context, path, force=False):
	"Import (insert/update) doclist. If the argument is a directory, all files ending with .json are imported"
	from frappe.core.page.data_import_tool import data_import_tool
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			data_import_tool.import_doc(path, overwrite=context.force)
		finally:
			frappe.destroy()

@click.command('import-csv')
@click.argument('path')
@click.option('--only-insert', default=False, is_flag=True, help='Do not overwrite existing records')
@click.option('--submit-after-import', default=False, is_flag=True, help='Submit document after importing it')
@click.option('--ignore-encoding-errors', default=False, is_flag=True, help='Ignore encoding errors while coverting to unicode')
@pass_context
def import_csv(context, path, only_insert=False, submit_after_import=False, ignore_encoding_errors=False):
	"Import CSV using data import tool"
	from frappe.core.page.data_import_tool import importer
	from frappe.utils.csvutils import read_csv_content
	site = get_site(context)

	with open(path, 'r') as csvfile:
		content = read_csv_content(csvfile.read())

	frappe.init(site=site)
	frappe.connect()

	try:
		importer.upload(content, submit_after_import=submit_after_import,
			ignore_encoding_errors=ignore_encoding_errors, overwrite=not only_insert,
			via_console=True)
		frappe.db.commit()
	except Exception:
		print frappe.get_traceback()

	frappe.destroy()

@click.command('bulk-rename')
@click.argument('doctype')
@click.argument('path')
@pass_context
def _bulk_rename(context, doctype, path):
	"Rename multiple records via CSV file"
	from frappe.model.rename_doc import bulk_rename
	from frappe.utils.csvutils import read_csv_content

	site = get_site(context)

	with open(path, 'r') as csvfile:
		rows = read_csv_content(csvfile.read())

	frappe.init(site=site)
	frappe.connect()

	bulk_rename(doctype, rows, via_console = True)

	frappe.destroy()

@click.command('mysql')
@pass_context
def mysql(context):
	"Start Mariadb console for a site"
	site = get_site(context)
	frappe.init(site=site)
	msq = find_executable('mysql')
	os.execv(msq, [msq, '-u', frappe.conf.db_name, '-p'+frappe.conf.db_password, frappe.conf.db_name, '-h', frappe.conf.db_host or "localhost", "-A"])

@click.command('console')
@pass_context
def console(context):
	"Start ipython console for a site"
	site = get_site(context)
	frappe.init(site=site)
	frappe.connect()
	frappe.local.lang = frappe.db.get_default("lang")
	import IPython
	IPython.embed()

@click.command('run-tests')
@click.option('--app', help="For App")
@click.option('--doctype', help="For DocType")
@click.option('--test', multiple=True, help="Specific test")
@click.option('--driver', help="For Travis")
@click.option('--module', help="Run tests in a module")
@click.option('--profile', is_flag=True, default=False)
@pass_context
def run_tests(context, app=None, module=None, doctype=None, test=(), driver=None, profile=False):
	"Run tests"
	import frappe.test_runner
	from frappe.utils import sel
	tests = test

	site = get_site(context)
	frappe.init(site=site)

	if frappe.conf.run_selenium_tests and False:
		sel.start(context.verbose, driver)

	try:
		ret = frappe.test_runner.main(app, module, doctype, context.verbose, tests=tests,
			force=context.force, profile=profile)
		if len(ret.failures) == 0 and len(ret.errors) == 0:
			ret = 0
	finally:
		pass
		if frappe.conf.run_selenium_tests:
			sel.close()

	sys.exit(ret)

@click.command('serve')
@click.option('--port', default=8000)
@click.option('--profile', is_flag=True, default=False)
@pass_context
def serve(context, port=None, profile=False, sites_path='.', site=None):
	"Start development web server"
	import frappe.app

	if not context.sites:
		site = None
	else:
		site = context.sites[0]

	frappe.app.serve(port=port, profile=profile, site=site, sites_path='.')

@click.command('request')
@click.argument('args')
@pass_context
def request(context, args):
	"Run a request as an admin"
	import frappe.handler
	import frappe.api
	for site in context.sites:
		try:
			frappe.init(site=site)
			frappe.connect()
			if "?" in args:
				frappe.local.form_dict = frappe._dict([a.split("=") for a in args.split("?")[-1].split("&")])
			else:
				frappe.local.form_dict = frappe._dict()

			if args.startswith("/api/method"):
				frappe.local.form_dict.cmd = args.split("?")[0].split("/")[-1]

			frappe.handler.execute_cmd(frappe.form_dict.cmd)

			print frappe.response
		finally:
			frappe.destroy()

@click.command('make-app')
@click.argument('destination')
@click.argument('app_name')
def make_app(destination, app_name):
	"Creates a boilerplate app"
	from frappe.utils.boilerplate import make_boilerplate
	make_boilerplate(destination, app_name)

@click.command('set-config')
@click.argument('key')
@click.argument('value')
@click.option('--as-dict', is_flag=True, default=False)
@pass_context
def set_config(context, key, value, as_dict=False):
	"Insert/Update a value in site_config.json"
	from frappe.installer import update_site_config
	import ast
	if as_dict:
		value = ast.literal_eval(value)
	for site in context.sites:
		frappe.init(site=site)
		update_site_config(key, value, validate=False)
		frappe.destroy()

@click.command('version')
def get_version():
	"Show the versions of all the installed apps"
	frappe.init('')
	for m in sorted(frappe.get_all_apps()):
		module = frappe.get_module(m)
		if hasattr(module, "__version__"):
			print "{0} {1}".format(m, module.__version__)

commands = [
	build,
	clear_cache,
	clear_website_cache,
	console,
	destroy_all_sessions,
	execute,
	export_csv,
	export_doc,
	export_fixtures,
	export_json,
	get_version,
	import_csv,
	import_doc,
	make_app,
	mysql,
	request,
	reset_perms,
	run_tests,
	serve,
	set_config,
	watch,
	_bulk_rename,
	add_to_email_queue,
]
