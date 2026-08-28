from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    daily_bid_target = fields.Integer(
        string="Daily Bid Target",
        default=40,
        config_parameter="sales_bidding.daily_bid_target",
        help="Default number of bids a salesperson should submit per day.",
    )