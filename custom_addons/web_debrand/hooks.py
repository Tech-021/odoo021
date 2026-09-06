import base64
import logging
import re

from odoo.tools import file_open

from .const import BRAND_NAME, BRAND_URL, FAVICON_FILE

_logger = logging.getLogger(__name__)

_POWERED_BY_LINK = re.compile(
    r'(Powered\s+by\s+<a\b[^>]*?\bhref=")https?://(?:www\.)?odoo\.com[^"]*("[^>]*>)\s*Odoo\s*(</a>)',
    flags=re.IGNORECASE,
)
_POWERED_BY_SPAN = re.compile(
    r'(<span class="odoo_link_text">)\s*Odoo\s*(</span>)',
    flags=re.IGNORECASE,
)


def post_init_hook(env):
    _set_web_app_name(env)
    _set_website_favicon(env)
    _debrand_mail_templates(env)


def _set_web_app_name(env):
    params = env["ir.config_parameter"].sudo()
    current = params.get_param("web.web_app_name")
    if not current or current == "Odoo":
        params.set_param("web.web_app_name", BRAND_NAME)


def _set_website_favicon(env):
    if "website" not in env:
        return
    with file_open(FAVICON_FILE, "rb") as f:
        payload = base64.b64encode(f.read())
    websites = env["website"].sudo().search([])
    if websites:
        websites.write({"favicon": payload})
        _logger.info("Updated favicon on %s website(s)", len(websites))


def _debrand_mail_templates(env):
    templates = env["mail.template"].sudo().search([("body_html", "ilike", "odoo.com")])
    updated = 0
    for template in templates:
        body = template.body_html or ""
        new_body = _POWERED_BY_LINK.sub(rf"\1{BRAND_URL}\2{BRAND_NAME}\3", body)
        new_body = _POWERED_BY_SPAN.sub(rf"\1{BRAND_NAME}\2", new_body)
        if new_body != body:
            template.body_html = new_body
            updated += 1
    if updated:
        _logger.info("Debranded Powered-by footer on %s mail templates", updated)
