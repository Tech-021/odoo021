/** @odoo-module **/

import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useService } from "@web/core/utils/hooks";
import { useState, useEffect } from "@odoo/owl";

class SalesBidMyListRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.sbStats = useState({ count: 0, target: 0, achievement: 0 });

        useEffect(
            () => { this.loadStats(); },
            () => [this.props.list.records.length]
        );
    }

    async loadStats() {
        const data = await this.orm.call("sales.bid", "get_my_today_stats", []);
        data.achievement = Math.round(data.achievement * 10) / 10;
        Object.assign(this.sbStats, data);
    }

    get formattedAchievement() {
        return (this.sbStats.achievement || 0).toFixed(1);
    }
    get achievementClass() {
        const pct = this.sbStats.achievement || 0;
        if (pct >= 100) return "o_sb_stat_success";
        if (pct >= 50) return "o_sb_stat_warning";
        return "o_sb_stat_danger";
    }
}
SalesBidMyListRenderer.template = "sales_bidding.SalesBidMyListRenderer";

export const sales_bid_my_list = {
    ...listView,
    Renderer: SalesBidMyListRenderer,
};

registry.category("views").add("sales_bid_my_list", sales_bid_my_list);