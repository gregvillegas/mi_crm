from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from customers.models import Customer

class Command(BaseCommand):
    help = 'Activate inactive customers'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--created-after')
        parser.add_argument('--created-before')

    def handle(self, *args, **options):
        qs = Customer.objects.filter(is_active=False)
        ca = options.get('created_after')
        cb = options.get('created_before')
        if ca:
            d = parse_date(ca)
            if d:
                qs = qs.filter(created_at__date__gte=d)
        if cb:
            d = parse_date(cb)
            if d:
                qs = qs.filter(created_at__date__lte=d)
        count = qs.count()
        if options.get('dry_run'):
            self.stdout.write(f'{count} inactive customers would be activated')
            return
        updated = qs.update(is_active=True)
        self.stdout.write(f'Activated {updated} inactive customers')
