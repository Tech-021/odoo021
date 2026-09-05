{
    'name': 'Attendance Slack Notifications',
    'version': '1.0',
    'category': 'Human Resources/Attendances',
    'summary': 'Post employee check-in and check-out events to Slack',
    'description': """
Whenever an employee checks in or out in Odoo Attendances, a message is posted
to the configured Slack incoming webhook (typically the #hr channel).
    """,
    'depends': ['hr_attendance'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'author': 'TECH 021',
    'license': 'LGPL-3',
}
