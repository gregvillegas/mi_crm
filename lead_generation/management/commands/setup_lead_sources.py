from django.core.management.base import BaseCommand
from lead_generation.models import LeadSource

class Command(BaseCommand):
    help = 'Create sample lead sources for testing'

    def handle(self, *args, **options):
        lead_sources = [
            {
                'name': 'Website Contact Form',
                'source_type': 'website',
                'description': 'Leads from company website contact form',
                'cost_per_lead': 25.00
            },
            {
                'name': 'Facebook Ads',
                'source_type': 'social_media', 
                'description': 'Facebook advertising campaigns',
                'cost_per_lead': 35.00
            },
            {
                'name': 'LinkedIn Outreach',
                'source_type': 'social_media',
                'description': 'Direct outreach via LinkedIn',
                'cost_per_lead': 15.00
            },
            {
                'name': 'Customer Referrals',
                'source_type': 'referral',
                'description': 'Referrals from existing customers',
                'cost_per_lead': 10.00
            },
            {
                'name': 'Cold Calling',
                'source_type': 'cold_calling',
                'description': 'Outbound cold calling campaigns',
                'cost_per_lead': 50.00
            },
            {
                'name': 'Email Marketing',
                'source_type': 'email_marketing',
                'description': 'Email newsletter and campaigns',
                'cost_per_lead': 20.00
            },
            {
                'name': 'Google Ads',
                'source_type': 'paid_search',
                'description': 'Google search advertising',
                'cost_per_lead': 40.00
            },
            {
                'name': 'Trade Shows',
                'source_type': 'trade_show',
                'description': 'Industry trade shows and events',
                'cost_per_lead': 100.00
            }
        ]
        
        created_count = 0
        for source_data in lead_sources:
            source, created = LeadSource.objects.get_or_create(
                name=source_data['name'],
                defaults=source_data
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created lead source: {source.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Lead source already exists: {source.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new lead sources')
        )
