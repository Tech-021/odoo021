{
    'name': 'Attendance Slack Notifications',
    'version': '1.1',
    'category': 'Human Resources/Attendances',
    'summary': 'Post employee check-in and check-out events to Slack',
    'description': """
Whenever an employee checks in or out in Odoo Attendances, a message is posted
to the configured Slack incoming webhook (typically the #hr channel).

Optional daily reminders list employees who have not checked in by a set time,
and employees who are still checked in at the end of the day.
    """,
    'depends': ['hr_attendance'],
    'data': [
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'author': 'TECH 021',
    'license': 'LGPL-3',
}
