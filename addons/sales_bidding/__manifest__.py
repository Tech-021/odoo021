{
    "name": "Sales Bidding",
    "version": "1.0.0",
    "category": "Sales",
    "summary": "Track Upwork and Freelancer bidding activity",
    "author": "Tech-021",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/sales_bidding_security.xml",
        "security/ir.model.access.csv",
        "views/sales_bid_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "application": True,
}