from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand
from django.utils import timezone

from sales_monitoring.models import SalesActivity
from teams.models import TeamMembership


ENGINEERING_EMAIL = 'service@microimageph.com'


class Command(BaseCommand):
    help = 'Send reminder emails for upcoming client meeting activities.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days-ahead',
            type=int,
            default=2,
            help='How many days ahead to notify for upcoming client meetings.',
        )
        parser.add_argument(
            '--activity-id',
            type=int,
            help='Send reminder only for one activity ID.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview recipients and activities without sending email.',
        )

    def handle(self, *args, **options):
        days_ahead = options['days_ahead']
        activity_id = options.get('activity_id')
        dry_run = options['dry_run']
        target_date = timezone.localdate() + timedelta(days=days_ahead)

        activities = SalesActivity.objects.select_related(
            'salesperson',
            'customer',
            'activity_type',
        ).filter(
            scheduled_start__date=target_date,
            status__in=['planned', 'in_progress'],
        )

        if activity_id:
            activities = activities.filter(id=activity_id)

        processed = 0
        sent = 0
        skipped = 0

        for activity in activities:
            processed += 1

            if not activity.is_client_meeting:
                skipped += 1
                continue

            if activity.meeting_notification_sent_for == activity.scheduled_start:
                skipped += 1
                continue

            recipients = self._resolve_recipients(activity)
            if not recipients:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping activity {activity.id} "{activity.title}" because no recipients were resolved.'
                    )
                )
                continue

            subject = f'Upcoming Client Meeting: {activity.title}'
            body = self._build_message(activity, days_ahead, recipients)

            if dry_run:
                self.stdout.write(
                    f'[DRY RUN] Activity {activity.id}: {activity.title} -> {", ".join(recipients)}'
                )
            else:
                email = EmailMessage(
                    subject=subject,
                    body=body,
                    from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', None) or 'no-reply@microimageph.com',
                    to=recipients,
                )
                email.send(fail_silently=False)
                activity.mark_meeting_notification_sent()
                sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Sent reminder for activity {activity.id} "{activity.title}" to {", ".join(recipients)}'
                    )
                )

        summary = (
            f'Processed {processed} activities. '
            f'{"Would send" if dry_run else "Sent"} {sent if not dry_run else processed - skipped}. '
            f'Skipped {skipped}.'
        )
        self.stdout.write(self.style.SUCCESS(summary))

    def _resolve_recipients(self, activity):
        recipients = set()

        try:
            membership = activity.salesperson.team_membership
        except TeamMembership.DoesNotExist:
            membership = None

        group = membership.group if membership else None
        team = group.team if group else None

        supervisor = getattr(group, 'supervisor', None)
        asm = getattr(team, 'asm', None)
        avp = getattr(team, 'avp', None)

        for user in [supervisor, asm, avp]:
            if user and user.is_active and user.email:
                recipients.add(user.email)

        if activity.engineer_required:
            recipients.add(ENGINEERING_EMAIL)

        return sorted(recipients)

    def _build_message(self, activity, days_ahead, recipients):
        customer_name = activity.customer.company_name if activity.customer else 'No customer linked'
        schedule = timezone.localtime(activity.scheduled_start).strftime('%b %d, %Y %I:%M %p')
        supervisor_note = activity.supervisor_notes or 'No supervisor notes yet.'
        engineer_line = 'Yes' if activity.engineer_required else 'No'

        return (
            f'This is a reminder that a Client Meeting activity is scheduled in {days_ahead} days.\n\n'
            f'Activity: {activity.title}\n'
            f'Customer: {customer_name}\n'
            f'Salesperson: {activity.salesperson.get_full_name() or activity.salesperson.username}\n'
            f'Scheduled Start: {schedule}\n'
            f'Status: {activity.get_status_display()}\n'
            f'Priority: {activity.get_priority_display()}\n'
            f'Engineer Required: {engineer_line}\n'
            f'Supervisor Notes: {supervisor_note}\n'
            f'Recipients: {", ".join(recipients)}\n\n'
            'Please coordinate attendance and preparation before the meeting schedule.'
        )
