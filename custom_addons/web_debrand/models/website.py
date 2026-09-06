import base64

from odoo import api, models
from odoo.tools import file_open

from odoo.addons.web_debrand.const import BRAND_COLOR, FAVICON_FILE


class Website(models.Model):
    _inherit = "website"

    @api.model
    def _web_debrand_apply_favicon(self):
        with file_open(FAVICON_FILE, "rb") as f:
            payload = base64.b64encode(f.read())
        websites = self.sudo().search([])
        if websites:
            websites.write({"favicon": payload})
            Assets = self.env["website.assets"]
            for website in websites:
                Assets.with_context(website_id=website.id).make_scss_customization(
                    "/website/static/src/scss/options/colors/user_color_palette.scss",
                    {"o-color-1": BRAND_COLOR},
                )
        return True
