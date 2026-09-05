/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { browser } from "@web/core/browser/browser";
import { _t } from "@web/core/l10n/translation";
import { useRef } from "@odoo/owl";

const STORAGE_KEY = "web_menu_modern.sidebar.collapsed";

function menuMatchesQuery(menu, query) {
    if (!query) {
        return true;
    }
    if (menu.name && menu.name.toLowerCase().includes(query)) {
        return true;
    }
    return (menu.childrenTree || []).some((child) => menuMatchesQuery(child, query));
}

function filterSectionTree(sections, query) {
    if (!query) {
        return sections;
    }
    const result = [];
    for (const section of sections) {
        const children = filterSectionTree(section.childrenTree || [], query);
        if (section.name?.toLowerCase().includes(query) || children.length) {
            result.push(children.length ? { ...section, childrenTree: children } : section);
        }
    }
    return result;
}

patch(NavBar, {
    template: "web_menu_modern.NavBar",
});

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this.sidebarSearch = useRef("sidebarSearch");
        this.state.collapsed = browser.localStorage.getItem(STORAGE_KEY) === "1";
        this.state.query = "";
    },

    get searchPlaceholder() {
        return _t("Search");
    },
    set searchPlaceholder(_) {},

    get collapseLabel() {
        return this.isSidebarCollapsed ? _t("Expand menu") : _t("Collapse menu");
    },
    set collapseLabel(_) {},

    get isWebsiteEditorActive() {
        return Boolean(this.shouldDisplayWebsiteSystray);
    },
    set isWebsiteEditorActive(_) {},

    get isSidebarCollapsed() {
        if (this.ui.isSmall) {
            return false;
        }
        return this.state.collapsed || this.isWebsiteEditorActive;
    },
    set isSidebarCollapsed(_) {},

    get filteredApps() {
        const apps = this.menuService.getApps();
        const query = this.state.query.trim().toLowerCase();
        if (!query) {
            return apps;
        }
        return apps.filter((app) => {
            if (app.name?.toLowerCase().includes(query)) {
                return true;
            }
            return menuMatchesQuery({ childrenTree: this._sectionsForApp(app) }, query);
        });
    },
    set filteredApps(_) {},

    async adapt() {
        this.currentAppSectionsExtra = [];
    },

    getAppIcon(app) {
        if (app.webIconData) {
            let src = app.webIconData;
            if (!src.startsWith("data:image") && !src.startsWith("/")) {
                const prefix = src.startsWith("P")
                    ? "data:image/svg+xml;base64,"
                    : "data:image/png;base64,";
                src = prefix + src.replace(/\s/g, "");
            }
            return { src };
        }
        if (app.webIcon && typeof app.webIcon === "object") {
            return app.webIcon;
        }
        if (app.webIcon && typeof app.webIcon === "string") {
            const [iconClass, color, backgroundColor] = app.webIcon.split(",");
            if (backgroundColor !== undefined) {
                return { iconClass, color, backgroundColor };
            }
        }
        return { src: "/web/static/img/default_icon_app.png" };
    },

    isAppExpanded(app) {
        if (this.isSidebarCollapsed) {
            return false;
        }
        if (this.state.query.trim()) {
            return true;
        }
        return this.currentApp && this.currentApp.id === app.id;
    },

    getAppSections(app) {
        const query = this.state.query.trim().toLowerCase();
        return filterSectionTree(this._sectionsForApp(app), query);
    },

    _sectionsForApp(app) {
        if (this.currentApp && this.currentApp.id === app.id) {
            return this.currentAppSections || [];
        }
        return this.menuService.getMenuAsTree(app.id).childrenTree || [];
    },

    sectionHotkey(index, depth) {
        if (depth || index >= 10) {
            return undefined;
        }
        return ((index + 1) % 10).toString();
    },

    onSearchInput(ev) {
        this.state.query = ev.target.value;
    },

    toggleCollapsed() {
        if (this.ui.isSmall || this.isWebsiteEditorActive) {
            return;
        }
        this.state.collapsed = !this.state.collapsed;
        if (this.state.collapsed) {
            this.state.query = "";
        }
        browser.localStorage.setItem(STORAGE_KEY, this.state.collapsed ? "1" : "0");
    },

    async expandAndFocusSearch() {
        if (this.state.collapsed && !this.isWebsiteEditorActive && !this.ui.isSmall) {
            this.state.collapsed = false;
            browser.localStorage.setItem(STORAGE_KEY, "0");
            await this.render(true);
        }
        this.sidebarSearch.el?.focus();
    },

    onAppSelected(app) {
        this.onNavBarDropdownItemSelection(app);
        this.state.query = "";
    },

    onSectionSelected(section) {
        this.onNavBarDropdownItemSelection(section);
        this.state.query = "";
        if (this.ui.isSmall) {
            this._closeAppMenuSidebar();
        }
    },
});
