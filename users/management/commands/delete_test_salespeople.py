from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_date
from django.db.models import Q
from users.models import User

class Command(BaseCommand):
    help = "Delete salesperson users used for testing (with safety filters)"

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Preview deletions without applying')
        parser.add_argument('--inactive-only', action='store_true', help='Limit to inactive users')
        parser.add_argument('--created-after', help='YYYY-MM-DD')
        parser.add_argument('--created-before', help='YYYY-MM-DD')
        parser.add_argument('--name-like', help='Fragments (pipe-separated) matched against username or full name')
        parser.add_argument('--email-domain', help='Limit to emails ending with this domain (e.g., @example.com)')
        parser.add_argument('--never-logged-in', action='store_true', help='Limit to users who never logged in (last_activity is null)')

    def handle(self, *args, **options):
        qs = User.objects.filter(role='salesperson')
        if options.get('inactive-only'):
            qs = qs.filter(is_active=False)
        ca = options.get('created_after')
        cb = options.get('created_before')
        if ca:
            d = parse_date(ca)
            if d:
                qs = qs.filter(date_joined__date__gte=d)
        if cb:
            d = parse_date(cb)
            if d:
                qs = qs.filter(date_joined__date__lte=d)
        name_like = options.get('name_like')
        if name_like:
            parts = [p.strip() for p in name_like.split('|') if p.strip()]
            if parts:
                cond = Q()
                for p in parts:
                    cond |= Q(username__icontains=p) | Q(first_name__icontains=p) | Q(last_name__icontains=p)
                qs = qs.filter(cond)
        email_domain = options.get('email_domain')
        if email_domain:
            dom = email_domain.strip().lower()
            qs = qs.filter(email__iendswith=dom)
        if options.get('never_logged_in'):
            qs = qs.filter(last_activity__isnull=True)

        count = qs.count()
        if options.get('dry_run'):
            self.stdout.write(f'{count} salesperson test users would be deleted')
            for u in qs[:50]:
                self.stdout.write(f' - {u.username} ({u.email})')
            if count > 50:
                self.stdout.write(f' ... and {count - 50} more')
            return

        deleted = 0
        for u in qs.iterator():
            u.delete()
            deleted += 1
        self.stdout.write(f'Deleted {deleted} salesperson test users')
