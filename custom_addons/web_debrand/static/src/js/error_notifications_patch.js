/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

const sessionExpired = {
    title: _t("Session Expired"),
    message: _t("Your session expired. The current page is about to be refreshed."),
    buttons: [
        {
            text: _t("Ok"),
            click: () => window.location.reload(true),
            close: true,
        },
    ],
};

registry
    .category("error_notifications")
    .add("odoo.http.SessionExpiredException", sessionExpired, { force: true })
    .add("werkzeug.exceptions.Forbidden", sessionExpired, { force: true });
