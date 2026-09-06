from odoo.http import request

from odoo.addons.web.controllers.webmanifest import WebManifest as WebWebManifest

from odoo.addons.web_debrand.const import (
    BRAND_BACKGROUND,
    BRAND_COLOR,
    BRAND_NAME,
    ICON_192_FILE,
    ICON_192_PATH,
    ICON_512_PATH,
)


class WebManifest(WebWebManifest):
    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        web_app_name = (
            request.env["ir.config_parameter"].sudo().get_param("web.web_app_name", BRAND_NAME)
        )
        if not web_app_name or web_app_name == "Odoo":
            web_app_name = BRAND_NAME
        manifest["name"] = web_app_name
        manifest["short_name"] = web_app_name
        manifest["background_color"] = BRAND_BACKGROUND
        manifest["theme_color"] = BRAND_COLOR
        manifest["icons"] = [
            {"src": ICON_192_PATH, "sizes": "192x192", "type": "image/png"},
            {"src": ICON_512_PATH, "sizes": "512x512", "type": "image/png"},
        ]
        return manifest

    def _icon_path(self):
        return ICON_192_FILE
