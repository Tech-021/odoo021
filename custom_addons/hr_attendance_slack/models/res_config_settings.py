import requests

from odoo import fields, models
from odoo.exceptions import UserError

from .hr_attendance import SLACK_WEBHOOK_PREFIXES


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    slack_attendance_enabled = fields.Boolean(
        string="Slack Attendance Notifications",
        config_parameter='hr_attendance_slack.enabled',
    )
    slack_attendance_webhook_url = fields.Char(
        string="Slack Incoming Webhook URL",
        config_parameter='hr_attendance_slack.webhook_url',
        groups='base.group_system',
    )

    def action_test_slack_attendance(self):
        self.ensure_one()
        webhook_url = (self.slack_attendance_webhook_url or '').strip()
        if not webhook_url:
            raise UserError(self.env._("Enter a Slack incoming webhook URL first, then save settings."))
        if not webhook_url.startswith(SLACK_WEBHOOK_PREFIXES):
            raise UserError(self.env._(
                "The URL must be a Slack incoming webhook starting with https://hooks.slack.com/."
            ))

        payload = {
            'text': 'Odoo attendance notifications are connected.',
            'blocks': [{
                'type': 'section',
                'text': {
                    'type': 'mrkdwn',
                    'text': ':white_check_mark: *Odoo attendance* notifications are connected.\nCheck-in and check-out events will be posted here.',
                },
            }],
        }
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=5,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise UserError(self.env._("Could not post to Slack: %s", exc)) from exc

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': self.env._("Test message sent to Slack."),
            },
        }
