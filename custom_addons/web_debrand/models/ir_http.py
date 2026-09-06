from odoo import models

from odoo.addons.web_debrand.const import BRAND_URL


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["support_url"] = BRAND_URL
        return result
