import json
import logging
from datetime import timedelta

import pytz
import requests

from odoo import api, fields, models, modules
from odoo.tools import format_date, format_datetime, format_duration, format_time
from odoo.tools.date_utils import sum_intervals

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
                return False
        return True

    @api.model
    def _cron_slack_attendance_reminders(self):
        """Post missing check-in / still-checked-in reminders to Slack once per day."""
        if not self._is_slack_attendance_enabled() or not self._get_slack_attendance_webhook_url():
            return
        self._send_slack_check_in_reminder()
        self._send_slack_check_out_reminder()

    @api.model
    def _send_slack_check_in_reminder(self, force=False):
        if not force and not self._slack_param_bool('hr_attendance_slack.reminder_check_in_enabled', True):
            return False
        if not force and not self._slack_reminder_should_run(
            'hr_attendance_slack.last_check_in_reminder_date',
            self._slack_param_float('hr_attendance_slack.reminder_check_in_hour', 9.5),
        ):
            return False

        missing = self._get_employees_missing_check_in()
        if missing is None:
            if not force:
                self._set_slack_reminder_sent_date('hr_attendance_slack.last_check_in_reminder_date')
            return False
        payload = self._prepare_slack_check_in_reminder_payload(missing)
        if not self._post_slack_reminder(payload):
            return False
        self._set_slack_reminder_sent_date('hr_attendance_slack.last_check_in_reminder_date')
        return True

    @api.model
    def _send_slack_check_out_reminder(self, force=False):
        if not force and not self._slack_param_bool('hr_attendance_slack.reminder_check_out_enabled', True):
            return False
        if not force and not self._slack_reminder_should_run(
            'hr_attendance_slack.last_check_out_reminder_date',
            self._slack_param_float('hr_attendance_slack.reminder_check_out_hour', 18.5),
        ):
            return False

        still_in = self._get_open_attendances_for_reminder()
        if not still_in and not force:
            self._set_slack_reminder_sent_date('hr_attendance_slack.last_check_out_reminder_date')
            return False
        payload = self._prepare_slack_check_out_reminder_payload(still_in)
        if not self._post_slack_reminder(payload):
            return False
        self._set_slack_reminder_sent_date('hr_attendance_slack.last_check_out_reminder_date')
        return True

    @api.model
    def _post_slack_reminder(self, payload):
        webhook_url = self._get_slack_attendance_webhook_url()
        if not webhook_url or not webhook_url.startswith(SLACK_WEBHOOK_PREFIXES):
            _logger.warning('Skipping Slack attendance reminder: webhook URL is missing or invalid.')
            return False
        return bool(self._post_slack_payloads(webhook_url, [json.dumps(payload)]))

    @api.model
    def _slack_reminder_timezone(self):
        company = self.env.company
        return (
            company.resource_calendar_id.tz
            or company.partner_id.tz
            or 'UTC'
        )

    @api.model
    def _slack_reminder_local_now(self):
        tz = pytz.timezone(self._slack_reminder_timezone())
        return pytz.utc.localize(fields.Datetime.now()).astimezone(tz)

    @api.model
    def _slack_reminder_should_run(self, last_sent_key, hour_float):
        local_now = self._slack_reminder_local_now()
        last_sent = self.env['ir.config_parameter'].sudo().get_param(last_sent_key, '')
        if last_sent == str(local_now.date()):
            return False
        hours = int(hour_float)
        minutes = int(round((hour_float - hours) * 60))
        if minutes == 60:
            hours += 1
            minutes = 0
        reminder_at = local_now.replace(hour=hours % 24, minute=minutes, second=0, microsecond=0)
        return local_now >= reminder_at

    @api.model
    def _set_slack_reminder_sent_date(self, key):
        local_now = self._slack_reminder_local_now()
        self.env['ir.config_parameter'].sudo().set_param(key, str(local_now.date()))

    @api.model
    def _slack_param_bool(self, key, default=False):
        value = self.env['ir.config_parameter'].sudo().get_param(key, 'True' if default else 'False')
        return value in ('True', 'true', '1')

    @api.model
    def _slack_param_float(self, key, default):
        value = self.env['ir.config_parameter'].sudo().get_param(key, str(default))
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @api.model
    def _get_employees_expected_today(self):
        employees = self.env['hr.employee'].sudo().search([('active', '=', True)])
        expected = self.env['hr.employee']
        now_utc = pytz.utc.localize(fields.Datetime.now())
        for employee in employees:
            tz = pytz.timezone(employee._get_tz())
            start = now_utc.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
            try:
                intervals = employee._get_expected_attendances(start, start + timedelta(days=1))
            except Exception:
                _logger.warning('Could not compute expected attendance for %s', employee.display_name, exc_info=True)
                continue
            if sum_intervals(intervals) > 0:
                expected |= employee
        return expected

    @api.model
    def _employee_local_day_bounds_utc(self, employee):
        tz = pytz.timezone(employee._get_tz())
        now_utc = pytz.utc.localize(fields.Datetime.now())
        start_local = now_utc.astimezone(tz).replace(hour=0, minute=0, second=0, microsecond=0)
        end_local = start_local + timedelta(days=1)
        return (
            start_local.astimezone(pytz.utc).replace(tzinfo=None),
            end_local.astimezone(pytz.utc).replace(tzinfo=None),
        )

    @api.model
    def _get_employees_missing_check_in(self):
        expected = self._get_employees_expected_today()
        if not expected:
            return None
        missing = self.env['hr.employee']
        for employee in expected:
            day_start, day_end = self._employee_local_day_bounds_utc(employee)
            has_check_in = self.env['hr.attendance'].sudo().search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', day_start),
                ('check_in', '<', day_end),
                ('in_mode', '!=', 'technical'),
            ], limit=1)
            if not has_check_in:
                missing |= employee
        return missing

    @api.model
    def _get_open_attendances_for_reminder(self):
        return self.env['hr.attendance'].sudo().search([
            ('check_out', '=', False),
            ('in_mode', '!=', 'technical'),
        ], order='check_in asc')

    @api.model
    def _prepare_slack_check_in_reminder_payload(self, missing_employees):
        today_label = format_date(self.env, self._slack_reminder_local_now().date())
        if not missing_employees:
            fallback = f'All expected employees have checked in ({today_label}).'
            heading = f':white_check_mark: *Everyone expected today has checked in* — {today_label}'
            return {
                'text': fallback,
                'blocks': [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': heading}}],
            }

        names = self._slack_employee_lines(missing_employees)
        count = len(missing_employees)
        fallback = f'{count} employee(s) have not checked in ({today_label}): ' + ', '.join(
            missing_employees.mapped('name')
        )
        heading = (
            f':warning: *{count} employee(s) have not checked in* — {today_label}\n'
            'Please check in on Odoo if you are working today.'
        )
        return {
            'text': fallback,
            'blocks': [
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': heading}},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': names}},
            ],
        }

    @api.model
    def _prepare_slack_check_out_reminder_payload(self, open_attendances):
        today_label = format_date(self.env, self._slack_reminder_local_now().date())
        if not open_attendances:
            fallback = f'Nobody is still checked in ({today_label}).'
            heading = f':white_check_mark: *Everyone who checked in has checked out* — {today_label}'
            return {
                'text': fallback,
                'blocks': [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': heading}}],
            }

        lines = []
        for attendance in open_attendances:
            employee = attendance.sudo().employee_id
            when = format_time(self.env, attendance.check_in, tz=employee._get_tz(), time_format='short')
            extra = f' ({employee.department_id.name})' if employee.department_id else ''
            lines.append(f'• *{employee.name}*{extra} — since {when}')
        count = len(open_attendances)
        fallback = f'{count} employee(s) are still checked in ({today_label}).'
        heading = (
            f':hourglass: *{count} employee(s) are still checked in* — {today_label}\n'
            'Please check out on Odoo if you have left.'
        )
        return {
            'text': fallback,
            'blocks': [
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': heading}},
                {'type': 'section', 'text': {'type': 'mrkdwn', 'text': '\n'.join(lines)}},
            ],
        }

    @api.model
    def _slack_employee_lines(self, employees):
        lines = []
        for employee in employees.sorted('name'):
            extra = f' ({employee.department_id.name})' if employee.department_id else ''
            lines.append(f'• *{employee.name}*{extra}')
        return '\n'.join(lines)
