from odoo.addons.web.controllers.database import Database as WebDatabase

from odoo.addons.web_debrand.const import BRAND_NAME, BRAND_URL, FAVICON_PATH, LOGO_PATH


class Database(WebDatabase):
    def _render_template(self, **d):
        html = super()._render_template(**d)
        html = str(html)
        replacements = (
            ("<title>Odoo</title>", f"<title>{BRAND_NAME}</title>"),
            ("/web/static/img/favicon.ico", FAVICON_PATH),
            ("/web/static/img/logo2.png", LOGO_PATH),
            ("your Odoo database manager", "your database manager"),
            ("Odoo database manager", "database manager"),
            ("Odoo needs to know", "the system needs to know"),
            ("Odoo online services", "online services"),
            ("https://www.odoo.com/privacy", f"{BRAND_URL}/privacy"),
        )
        for old, new in replacements:
            html = html.replace(old, new)
        return html
