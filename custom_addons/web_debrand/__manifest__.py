# -*- coding: utf-8 -*-
{
    "name": "Zero To One Branding",
    "version": "1.1",
    "category": "Hidden",
    "summary": "Replace Odoo product branding with Zero To One",
    "description": """
Replaces user-facing Odoo names, favicons, PWA metadata, About text,
and Powered-by footers with Zero To One branding. Core Odoo files are
left unchanged so upgrades stay safer.
    """,
    "depends": [
        "web",
        "mail",
        "portal",
        "website",
        "auth_signup",
        "hr_attendance",
        "digest",
        "base_setup",
        "marketing_card",
    ],
    "data": [
        "data/ir_config_parameter.xml",
        "data/website_favicon.xml",
        "views/webclient_templates.xml",
        "views/portal_templates.xml",
        "views/website_templates.xml",
        "views/mail_templates.xml",
        "views/auth_signup_templates.xml",
        "views/digest_templates.xml",
        "views/discuss_templates.xml",
        "views/marketing_card_templates.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "web._assets_primary_variables": [
            (
                "before",
                "web/static/src/scss/primary_variables.scss",
                "web_debrand/static/src/scss/primary_variables.scss",
            ),
        ],
        "web._assets_core": [
            "web_debrand/static/src/js/title_service_patch.js",
            "web_debrand/static/src/js/error_dialogs_patch.js",
            "web_debrand/static/src/xml/core_templates.xml",
        ],
        "web.assets_backend": [
            "web_debrand/static/src/scss/backend_colors.scss",
            "web_debrand/static/src/xml/res_config_edition.xml",
            "web_debrand/static/src/xml/kiosk.xml",
        ],
        "web.assets_frontend": [
            "web_debrand/static/src/js/error_notifications_patch.js",
        ],
        "hr_attendance.assets_public_attendance": [
            "web_debrand/static/src/xml/kiosk.xml",
        ],
    },
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": False,
    "author": "TECH 021",
    "website": "https://www.tech-021.com",
    "license": "LGPL-3",
}
