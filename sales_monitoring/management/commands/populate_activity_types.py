from django.core.management.base import BaseCommand
from sales_monitoring.models import ActivityType

class Command(BaseCommand):
    help = 'Populate default activity types for sales monitoring'

    def handle(self, *args, **options):
        activity_types = [
            {
                'name': 'Phone Call',
                'description': 'Phone calls to customers and prospects',
                'icon': 'fas fa-phone',
                'color': 'primary',
                'requires_customer': True,
            },
            {
                'name': 'Meeting',
                'description': 'In-person or virtual meetings with customers',
                'icon': 'fas fa-handshake',
                'color': 'success',
                'requires_customer': True,
            },
            {
                'name': 'Email',
                'description': 'Email communications and follow-ups',
                'icon': 'fas fa-envelope',
                'color': 'info',
                'requires_customer': True,
            },
            {
                'name': 'Proposal',
                'description': 'Creating and sending sales proposals',
                'icon': 'fas fa-file-contract',
                'color': 'warning',
                'requires_customer': True,
            },
            {
                'name': 'Task',
                'description': 'Administrative and preparatory tasks',
                'icon': 'fas fa-clipboard-check',
                'color': 'secondary',
                'requires_customer': False,
            },
            {
                'name': 'Demo',
                'description': 'Product demonstrations and presentations',
                'icon': 'fas fa-desktop',
                'color': 'purple',
                'requires_customer': True,
            },
            {
                'name': 'Follow-up',
                'description': 'Follow-up activities after initial contact',
                'icon': 'fas fa-redo',
                'color': 'dark',
                'requires_customer': True,
            },
            {
                'name': 'Research',
                'description': 'Customer and market research activities',
                'icon': 'fas fa-search',
                'color': 'light',
                'requires_customer': False,
            },
        ]

        created_count = 0
        for activity_data in activity_types:
            activity_type, created = ActivityType.objects.get_or_create(
                name=activity_data['name'],
                defaults=activity_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created activity type: {activity_type.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Activity type already exists: {activity_type.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new activity types')
        )
