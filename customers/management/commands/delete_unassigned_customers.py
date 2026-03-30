from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db.models import Q
from customers.models import Customer

class Command(BaseCommand):
    help = 'Delete customers without assigned salesperson'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--inactive-only', action='store_true')
        parser.add_argument('--created-after')
        parser.add_argument('--created-before')
        parser.add_argument('--name-like', help='Regex or contains fragment(s), separated by |')

    def handle(self, *args, **options):
        qs = Customer.objects.filter(salesperson__isnull=True)
        if options.get('inactive-only'):
            qs = qs.filter(is_active=False)
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
        name_like = options.get('name_like')
        if name_like:
            parts = [p.strip() for p in name_like.split('|') if p.strip()]
            if parts:
                cond = Q()
                for p in parts:
                    cond |= Q(company_name__icontains=p)
                qs = qs.filter(cond)
        count = qs.count()
        if options.get('dry_run'):
            self.stdout.write(f'{count} unassigned customers would be deleted')
            return
        deleted = 0
        for c in qs.iterator():
            c.delete()
            deleted += 1
        self.stdout.write(f'Deleted {deleted} unassigned customers')
