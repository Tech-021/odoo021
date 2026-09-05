import json
import logging

import requests

from odoo import api, models, modules
from odoo.tools import format_datetime, format_duration

_logger = logging.getLogger(__name__)

SLACK_WEBHOOK_PREFIXES = (
    'https://hooks.slack.com/',
    'https://hooks.slack-gov.com/',
)

CHECK_IN_MODE_LABELS = {
    'kiosk': 'Kiosk',
    'systray': 'Odoo',
    'manual': 'Manual',
    'technical': 'Technical',
}
CHECK_OUT_MODE_LABELS = {
    **CHECK_IN_MODE_LABELS,
    'auto_check_out': 'Automatic',
}


class HrAttendance(models.Model):
    _inherit = 'hr.attendance'

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records.filtered(lambda attendance: not attendance.check_out)._slack_notify_attendance('check_in')
        return records

    def write(self, vals):
        checking_out = bool(vals.get('check_out'))
        to_notify = self.filtered(lambda attendance: not attendance.check_out) if checking_out else self.browse()
        result = super().write(vals)
        if checking_out:
            to_notify._slack_notify_attendance('check_out')
        return result

    def _slack_notify_attendance(self, event):
        """Queue a Slack message for check-in or check-out, without blocking attendance."""
        if not self or self.env.context.get('import_file') or self.env.context.get('install_mode'):
            return
        webhook_url = self._get_slack_attendance_webhook_url()
        if not webhook_url or not self._is_slack_attendance_enabled():
            return
        if not webhook_url.startswith(SLACK_WEBHOOK_PREFIXES):
            _logger.warning('Skipping Slack attendance notification: webhook URL is not a Slack incoming webhook.')
            return

        payloads = []
        for attendance in self:
            mode = attendance.in_mode if event == 'check_in' else attendance.out_mode
            if mode == 'technical':
                continue
            payloads.append(attendance._prepare_slack_attendance_payload(event))
        if not payloads:
            return

        encoded_payloads = [json.dumps(payload) for payload in payloads]
        if modules.module.current_test:
            self._post_slack_payloads(webhook_url, encoded_payloads)
            return

        @self.env.cr.postcommit.add
        def _post_slack_after_commit():
            self._post_slack_payloads(webhook_url, encoded_payloads)

    def _prepare_slack_attendance_payload(self, event):
        self.ensure_one()
        employee = self.sudo().employee_id
        tz = employee._get_tz()
        name = employee.name
        department = employee.department_id.name
        job_title = employee.job_title
        timestamp = self.check_in if event == 'check_in' else self.check_out
        when = format_datetime(self.env, timestamp, tz=tz, dt_format='short')
        mode_labels = CHECK_IN_MODE_LABELS if event == 'check_in' else CHECK_OUT_MODE_LABELS
        mode = self.in_mode if event == 'check_in' else self.out_mode
        location = self.in_location if event == 'check_in' else self.out_location

        if event == 'check_in':
            fallback = f'{name} checked in at {when}'
            heading = f':large_green_circle: *{name}* checked in'
        else:
            worked = format_duration(self.worked_hours)
            fallback = f'{name} checked out at {when} (worked {worked})'
            heading = f':large_red_circle: *{name}* checked out'

        fields_mrkdwn = [
            {'type': 'mrkdwn', 'text': f'*Time*\n{when}'},
        ]
        if event == 'check_out':
            fields_mrkdwn.append({'type': 'mrkdwn', 'text': f'*Worked*\n{worked}'})
        if department:
            fields_mrkdwn.append({'type': 'mrkdwn', 'text': f'*Department*\n{department}'})
        if job_title:
            fields_mrkdwn.append({'type': 'mrkdwn', 'text': f'*Role*\n{job_title}'})
        if mode and mode in mode_labels:
            fields_mrkdwn.append({'type': 'mrkdwn', 'text': f'*Source*\n{mode_labels[mode]}'})
        if location:
            fields_mrkdwn.append({'type': 'mrkdwn', 'text': f'*Location*\n{location}'})

        return {
            'text': fallback,
            'blocks': [
                {
                    'type': 'section',
                    'text': {'type': 'mrkdwn', 'text': heading},
                },
                {
                    'type': 'section',
                    'fields': fields_mrkdwn,
                },
            ],
        }

    @api.model
    def _is_slack_attendance_enabled(self):
        return self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendance_slack.enabled', 'False'
        ) in ('True', 'true', '1')

    @api.model
    def _get_slack_attendance_webhook_url(self):
        return (self.env['ir.config_parameter'].sudo().get_param(
            'hr_attendance_slack.webhook_url', ''
        ) or '').strip()

    @api.model
    def _post_slack_payloads(self, webhook_url, encoded_payloads):
        headers = {'Content-Type': 'application/json'}
        for body in encoded_payloads:
            try:
                response = requests.post(webhook_url, data=body, headers=headers, timeout=5)
                response.raise_for_status()
            except requests.exceptions.RequestException:
                _logger.warning('Failed to post attendance notification to Slack.', exc_info=True)
