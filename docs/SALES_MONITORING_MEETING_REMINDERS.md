# Sales Monitoring: Client Meeting Reminder Emails

This document describes how the client meeting reminder script works and how to run it reliably in production.

## What It Is

The reminders are sent by a Django management command:

- [send_meeting_activity_reminders.py](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py)

It sends email reminders for upcoming Sales Monitoring activities that qualify as a “Client Meeting”.

## When an Activity Qualifies

The command selects activities that match all of the following:

- `scheduled_start__date == (today + days_ahead)`
- `status` is `planned` or `in_progress`
- `activity.is_client_meeting` is `True` (based on activity type name or meeting_details)

Reference:
- Activity query: [send_meeting_activity_reminders.py](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py#L40-L49)
- Client meeting detection: [SalesActivity.is_client_meeting](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/models.py#L119-L124)

## Recipient Rules

For each qualifying activity, the command resolves recipients from the salesperson’s team structure:

- Group Supervisor (if set, active, has email)
- Team ASM (if set, active, has email)
- Team AVP (if set, active, has email)
- Engineering email `service@microimageph.com` if `engineer_required=True`

Reference:
- Recipient resolution: [_resolve_recipients](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py#L109-L131)

If no recipients can be resolved, the activity is skipped and a warning is printed to stdout.

## Duplicate-Send Protection (Idempotency)

The command avoids sending duplicate reminders for the same schedule by checking:

- If `meeting_notification_sent_for == scheduled_start`, it skips sending.

After a successful send, it updates:

- `meeting_notification_sent_at = now()`
- `meeting_notification_sent_for = scheduled_start`

Reference:
- Skip logic: [send_meeting_activity_reminders.py](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py#L65-L68)
- Mark-as-sent: [SalesActivity.mark_meeting_notification_sent](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/models.py#L134-L138)

Practical effect:
- Safe to run multiple times a day.
- If the meeting time changes (`scheduled_start` changes), the next run will send again for the new schedule (because the stored `meeting_notification_sent_for` no longer matches).

## Email Contents

The email body includes:

- Activity title
- Customer name
- Salesperson name
- Scheduled start (localized via `timezone.localtime`)
- Status, priority
- Engineer required
- Supervisor notes
- Recipient list

Reference:
- Email build: [_build_message](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py#L133-L151)

## How To Run (Manual)

From the directory containing `manage.py`:

```bash
python manage.py send_meeting_activity_reminders
```

Useful options:

- Preview only (no email is sent):

```bash
python manage.py send_meeting_activity_reminders --dry-run
```

- Change how far ahead to notify:

```bash
python manage.py send_meeting_activity_reminders --days-ahead 1
python manage.py send_meeting_activity_reminders --days-ahead 3
```

- Send for a specific activity only:

```bash
python manage.py send_meeting_activity_reminders --activity-id 1234
```

Reference:
- CLI options: [add_arguments](file:///Users/greg/Documents/trae_projects/mi_crm/sales_monitoring/management/commands/send_meeting_activity_reminders.py#L18-L35)

## How To Run (Production Scheduling)

This command is not scheduled automatically inside the app (no Celery/Beat configuration in the repo). In production, it should be run by an OS scheduler (cron) or a process manager timer.

### Recommended Cron Setup

Since the default is `--days-ahead 2`, a daily schedule works well. Example: run every day at 8:00 AM server time:

```text
0 8 * * * cd /path/to/your/mi_crm && /path/to/your/venv/bin/python manage.py send_meeting_activity_reminders >> /path/to/your/mi_crm/logs/meeting_reminders.log 2>&1
```

If you want reminders to be more responsive to newly-created meetings, you can run it hourly:

```text
0 * * * * cd /path/to/your/mi_crm && /path/to/your/venv/bin/python manage.py send_meeting_activity_reminders >> /path/to/your/mi_crm/logs/meeting_reminders.log 2>&1
```

Notes:
- Ensure the server timezone matches your intended reminder behavior (Django uses `timezone.localdate()` and `timezone.localtime()`).
- Ensure your email settings are configured correctly (`DEFAULT_FROM_EMAIL`, email backend/SMTP).

## Operational Notes

- If `scheduled_start` is empty, the activity will never be selected by this command.
- The command uses `EmailMessage(...).send(fail_silently=False)`, so SMTP failures will raise an error and cron will record it in logs.
- The command prints a summary at the end: processed/sent/skipped.

