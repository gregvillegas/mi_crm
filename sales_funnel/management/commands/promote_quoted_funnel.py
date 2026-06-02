from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from sales_funnel.models import SalesFunnel


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--today', type=str, default='')

    def handle(self, *args, **options):
        today_raw = (options.get('today') or '').strip()
        if today_raw:
            today = datetime.strptime(today_raw, '%Y-%m-%d').date()
        else:
            today = timezone.localdate()

        week_start = today - timedelta(days=today.weekday())
        threshold = Decimal('500000')

        qs = (
            SalesFunnel.objects
            .filter(
                is_active=True,
                is_closed=False,
                deal_outcome='active',
                stage='quoted',
                date_created__lt=week_start,
            )
            .select_related('proposal')
        )

        project_ids = []
        services_ids = []
        for entry in qs:
            if entry.display_retail >= threshold:
                project_ids.append(entry.id)
            else:
                services_ids.append(entry.id)

        updated_project = 0
        updated_services = 0

        if project_ids:
            updated_project = SalesFunnel.objects.filter(id__in=project_ids).update(stage='project')
        if services_ids:
            updated_services = SalesFunnel.objects.filter(id__in=services_ids).update(stage='services')

        self.stdout.write(
            f'Promoted quoted funnel entries older than {week_start}: '
            f'green={updated_project}, blue={updated_services}.'
        )

