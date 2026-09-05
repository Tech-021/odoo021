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
    slack_reminder_check_in_enabled = fields.Boolean(
        string="Missing Check-in Reminder",
        config_parameter='hr_attendance_slack.reminder_check_in_enabled',
        default=True,
    )
    slack_reminder_check_in_hour = fields.Float(
        string="Check-in reminder time",
        config_parameter='hr_attendance_slack.reminder_check_in_hour',
        default=9.5,
    )
    slack_reminder_check_out_enabled = fields.Boolean(
        string="Missing Check-out Reminder",
        config_parameter='hr_attendance_slack.reminder_check_out_enabled',
        default=True,
    )
    slack_reminder_check_out_hour = fields.Float(
        string="Check-out reminder time",
        config_parameter='hr_attendance_slack.reminder_check_out_hour',
        default=18.5,
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

    def action_send_slack_check_in_reminder(self):
        self.ensure_one()
        self._require_slack_webhook()
        sent = self.env['hr.attendance']._send_slack_check_in_reminder(force=True)
        return self._slack_reminder_notification(
            self.env._("Missing check-in reminder sent to Slack.") if sent else
            self.env._("No check-in reminder sent. Nobody is expected to work today.")
        )

    def action_send_slack_check_out_reminder(self):
        self.ensure_one()
        self._require_slack_webhook()
        self.env['hr.attendance']._send_slack_check_out_reminder(force=True)
        return self._slack_reminder_notification(
            self.env._("Still-checked-in reminder sent to Slack.")
        )

    def _require_slack_webhook(self):
        webhook_url = (self.slack_attendance_webhook_url or '').strip()
        if not webhook_url:
            raise UserError(self.env._("Enter a Slack incoming webhook URL first, then save settings."))

    def _slack_reminder_notification(self, message):
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': message,
            },
        }
