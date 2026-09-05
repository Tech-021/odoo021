-- Remove Slack webhook credentials from neutralized copies of the database.
UPDATE ir_config_parameter
SET value = ''
WHERE key IN ('hr_attendance_slack.webhook_url', 'hr_attendance_slack.enabled');
