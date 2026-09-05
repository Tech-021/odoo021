from unittest.mock import patch

from odoo.tests.common import TransactionCase, tagged


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
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Ada Lovelace',
            'job_title': 'Engineer',
            'ruleset_id': False,
        })

    def test_check_in_posts_to_slack(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.raise_for_status = lambda: None
            attendance = self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-06 04:00:00',
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
                'check_in': '2026-09-06 04:00:00',
            })
            mock_post.reset_mock()
            attendance.write({'check_out': '2026-09-06 12:00:00'})
            mock_post.assert_called_once()
            body = mock_post.call_args.kwargs['data']
            self.assertIn('checked out', body)
            self.assertIn('Ada Lovelace', body)

    def test_complete_attendance_create_does_not_notify(self):
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-06 04:00:00',
                'check_out': '2026-09-06 12:00:00',
            })
            mock_post.assert_not_called()

    def test_disabled_setting_skips_slack(self):
        self.env['ir.config_parameter'].sudo().set_param('hr_attendance_slack.enabled', 'False')
        with patch('odoo.addons.hr_attendance_slack.models.hr_attendance.requests.post') as mock_post:
            self.env['hr.attendance'].create({
                'employee_id': self.employee.id,
                'check_in': '2026-09-06 04:00:00',
            })
            mock_post.assert_not_called()
