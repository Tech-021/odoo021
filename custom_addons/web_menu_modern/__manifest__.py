# -*- coding: utf-8 -*-
{
    "name": "Modern Finder Menu",
    "version": "1.0",
    "category": "Hidden",
    "summary": "Finder-style left sidebar and slim top chrome for the backend",
    "description": """
Replaces the purple top application bar with a macOS-inspired sidebar
and a slim top chrome. Core menu data and services are unchanged.
    """,
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "web_menu_modern/static/src/webclient/navbar_patch.js",
            "web_menu_modern/static/src/webclient/webclient_patch.js",
            "web_menu_modern/static/src/webclient/navbar.xml",
            "web_menu_modern/static/src/webclient/webclient_layout.scss",
            "web_menu_modern/static/src/webclient/sidebar.scss",
            "web_menu_modern/static/src/webclient/dropdown.scss",
        ],
        "web.assets_web_dark": [
            "web_menu_modern/static/src/webclient/sidebar.dark.scss",
        ],
    },
    "installable": True,
    "application": False,
    "author": "TECH 021",
    "license": "LGPL-3",
}
