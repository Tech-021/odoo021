from unittest.mock import patch

from odoo.tests.common import TransactionCase, freeze_time, tagged


@tagged('post_install', '-at_install')
class TestHrAttendanceSlack(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.enabled', 'True')
        cls.env['ir.config_parameter'].sudo().set_param(
            'hr_attendance_slack.webhook_url',
            'https://hooks.slack.com/services/T000/B000/XXX',
        )
        cls.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.reminder_check_in_enabled', 'True')
        cls.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.reminder_check_in_hour', '9.5')
        cls.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.reminder_check_out_enabled', 'True')
        cls.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.reminder_check_out_hour', '18.5')
        if cls.env.company.resource_calendar_id:
            cls.env.company.resource_calendar_id.tz = 'UTC'
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Ada Lovelace',
            'job_title': 'Engineer',
            'ruleset_id': False,
        })
        cls.other_employee = cls.env['hr.employee'].create({
            'name': 'Alan Turing',
            'job_title': 'Analyst',
            'ruleset_id': False,
        })

    def test_check_in_posts_to_slack(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-07 08:00:00',
            })
            mock_post.assert_called_once()
            _args, kwargs = mock_post.call_args
            body = kwargs['data']
            self.assertIn('Ada Lovelace', body)
            self.assertIn('checked in', body)
            self.assertTrue(attendance)

    def test_check_out_posts_to_slack(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-07 08:00:00',
            })
            mock_post.reset_mock()
            attendance.write({'check_out': '2026-09-07 17:00:00'})
            mock_post.assert_called_once()
            body = mock_post.call_args.kwargs['data']
            self.assertIn('checked out', body)
            self.assertIn('Ada Lovelace', body)

    def test_complete_attendance_create_does_not_notify(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-07 08:00:00',
                'check_out': '2026-09-07 17:00:00',
            })
            mock_post.assert_not_called()

    def test_disabled_setting_skips_slack(self):
        self.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.enabled', 'False')
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-07 08:00:00',
            })
            mock_post.assert_not_called()

    @freeze_time('2026-09-07 09:35:00')
    def test_check_in_reminder_lists_missing_employees(self):
        Attendance = self.env['hr.attendance']
        with patch.object(type(Attendance), '_get_employees_expected_today', return_value=self.employee | self.other_employee):
            with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
                mock_post.return_value.status_code = 200
                mock_post.return_value.raise_for_status = lambda: None
                Attendance.create({
                    'employee_id': self.employee.id,
                    'check_in': '2026-09-07 08:00:00',
                })
                mock_post.reset_mock()
                sent = Attendance._send_slack_check_in_reminder(force=True)
                self.assertTrue(sent)
                mock_post.assert_called_once()
                body = mock_post.call_args.kwargs['data']
                self.assertIn('have not checked in', body)
                self.assertIn('Alan Turing', body)
                self.assertNotIn('Ada Lovelace', body)

    @freeze_time('2026-09-07 08:00:00')
    def test_check_in_reminder_waits_until_configured_time(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            sent = self.env['hr.attendance']._send_slack_check_in_reminder()
            self.assertFalse(sent)
            mock_post.assert_not_called()

    @freeze_time('2026-09-07 18:40:00')
    def test_check_out_reminder_lists_open_attendances(self):
        Attendance = self.env['hr.attendance']
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            attendance = Attendance.create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-07 08:00:00',
            })
            mock_post.reset_mock()
            with patch.object(type(Attendance), '_get_open_attendances_for_reminder', return_value=attendance):
                sent = Attendance._send_slack_check_out_reminder(force=True)
            self.assertTrue(sent)
            mock_post.assert_called_once()
            body = mock_post.call_args.kwargs['data']
            self.assertIn('still checked in', body)
            self.assertIn('Ada Lovelace', body)
