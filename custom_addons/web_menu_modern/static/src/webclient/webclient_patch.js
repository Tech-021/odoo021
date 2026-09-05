/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "@web/core/utils/patch";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        onMounted(() => {
            document.querySelector(".o_web_client")?.classList.add("o_webclient_sidebar");
        });
        onWillUnmount(() => {
            document.querySelector(".o_web_client")?.classList.remove("o_webclient_sidebar");
        });
    },
});
