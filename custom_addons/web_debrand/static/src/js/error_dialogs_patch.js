/** @odoo-module **/

import {
    ClientErrorDialog,
    ErrorDialog,
    NetworkErrorDialog,
    RPCErrorDialog,
    WarningDialog,
} from "@web/core/errors/error_dialogs";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

ErrorDialog.title = _t("Error");
ClientErrorDialog.title = _t("Client Error");
NetworkErrorDialog.title = _t("Network Error");

function withoutOdooPrefix(title) {
    return title ? title.replace(/^Odoo\s+/i, "") : title;
}

patch(RPCErrorDialog.prototype, {
    inferTitle() {
        super.inferTitle();
        if (this.title) {
            this.title = withoutOdooPrefix(this.title);
        }
    },
});

patch(WarningDialog.prototype, {
    inferTitle() {
        const title = super.inferTitle();
        return withoutOdooPrefix(title) || _t("Warning");
    },
});
