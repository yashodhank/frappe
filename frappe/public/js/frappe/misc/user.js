// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// MIT License. See license.txt

// misc user functions

frappe.user_info = function(uid) {
	if(!uid)
		uid = user;

	if(uid.toLowerCase()==="bot") {
		return {
			fullname: __("Bot"),
			image: "/assets/frappe/images/ui/bot.png",
			abbr: "B"
		}
	}

	if(!(frappe.boot.user_info && frappe.boot.user_info[uid])) {
		var user_info = {
			fullname: toTitle(uid.split("@")[0]) || "Unknown"
		};
	} else {
		var user_info = frappe.boot.user_info[uid];
	}

	user_info.abbr = frappe.get_abbr(user_info.fullname);
	user_info.color = frappe.get_palette(user_info.fullname);

	return user_info;
}

frappe.ui.set_user_background = function(src, selector, style) {
	if(!selector) selector = "#page-desktop";
	if(!style) style = "Fill Screen";
	if(src) {
		var background = repl('background: url("%(src)s") center center;', {src: src});
	} else {
		var background = "background-color: #4B4C9D;";
	}

	frappe.dom.set_style(repl('%(selector)s { \
		%(background)s \
		background-attachment: fixed; \
		%(style)s \
	}', {
		selector:selector,
		background:background,
		style: style==="Fill Screen" ? "background-size: cover;" : ""
	}));
}

frappe.provide('frappe.user');

$.extend(frappe.user, {
	name: (frappe.boot ? frappe.boot.user.name : 'Guest'),
	full_name: function(uid) {
		return uid===user ?
			__("You") :
			frappe.user_info(uid).fullname;
	},
	image: function(uid) {
		return frappe.user_info(uid).image;
	},
	abbr: function(uid) {
		return frappe.user_info(uid).abbr;
	},
	has_role: function(rl) {
		if(typeof rl=='string')
			rl = [rl];
		for(var i in rl) {
			if((frappe.boot ? frappe.boot.user.roles : ['Guest']).indexOf(rl[i])!=-1)
				return true;
		}
	},
	get_desktop_items: function() {
		// hide based on permission
		modules_list = $.map(frappe.boot.desktop_icons, function(icon) {
			var m = icon.module_name;
			var type = frappe.modules[m] && frappe.modules[m].type;

			if(frappe.boot.user.allow_modules.indexOf(m) === -1) return null;

			var ret = null;
			switch(type) {
				case "module":
					if(frappe.boot.user.allow_modules.indexOf(m)!=-1 || frappe.modules[m].is_help)
						ret = m;
					break;
				case "page":
					if(frappe.boot.allowed_pages.indexOf(frappe.modules[m].link)!=-1)
						ret = m;
					break;
				case "list":
					if(frappe.model.can_read(frappe.modules[m]._doctype))
						ret = m;
					break;
				case "view":
					ret = m;
					break;
				case "setup":
					if(frappe.user.has_role("System Manager") || frappe.user.has_role("Administrator"))
						ret = m;
					break;
				default:
					ret = m;
			}

			return ret;
		});

		return modules_list;
	},

	is_module: function(m) {
		var icons = frappe.get_desktop_icons();
		for(var i=0; i<icons.length; i++) {
			if(m===icons[i].module_name) return true;
		}
		return false;
	},

	is_report_manager: function() {
		return frappe.user.has_role(['Administrator', 'System Manager', 'Report Manager']);
	},

	get_formatted_email: function(email) {
		var fullname = frappe.user.full_name(email);

		if (!fullname) {
			return email;
		} else {
			// to quote or to not
			var quote = '';

			// only if these special characters are found
			// why? To make the output same as that in python!
			if (fullname.search(/[\[\]\\()<>@,:;".]/) !== -1) {
				quote = '"';
			}

			return repl('%(quote)s%(fullname)s%(quote)s <%(email)s>', {
				fullname: fullname,
				email: email,
				quote: quote
			});
		}
	}
});

frappe.session_alive = true;
$(document).bind('mousemove', function() {
	if(frappe.session_alive===false) {
		$(document).trigger("session_alive");
	}
	frappe.session_alive = true;
	if(frappe.session_alive_timeout)
		clearTimeout(frappe.session_alive_timeout);
	frappe.session_alive_timeout = setTimeout('frappe.session_alive=false;', 30000);
});