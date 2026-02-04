from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import models, transaction
from datetime import datetime, timedelta
from lead_generation.models import Lead, LeadSource, LeadActivity
from lead_generation.scoring_engine import LeadScoringEngine
import random

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample leads for testing the scoring system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Number of sample leads to create (default: 20)',
        )
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing leads before creating new ones',
        )

    def handle(self, *args, **options):
        count = options['count']
        
        if options['reset']:
            self.stdout.write('Deleting existing leads...')
            Lead.objects.all().delete()
        
        # Get available lead sources and users
        lead_sources = list(LeadSource.objects.all())
        users = list(User.objects.filter(is_active=True))
        
        if not lead_sources:
            self.stdout.write(self.style.ERROR('No lead sources found. Run setup_lead_sources first.'))
            return
            
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Create users first.'))
            return
        
        # Sample data for leads
        companies = [
            'TechCorp Solutions', 'Global Industries Inc', 'Innovation Labs',
            'Future Systems Ltd', 'Digital Dynamics', 'Enterprise Solutions',
            'Smart Technologies', 'Advanced Analytics Co', 'Cloud Systems Inc',
            'Data Insights Ltd', 'NextGen Software', 'Precision Engineering',
            'Strategic Consulting', 'Modern Manufacturing', 'Dynamic Healthcare',
            'Financial Partners LLC', 'Educational Services', 'Energy Solutions',
            'Retail Innovations', 'Hospitality Group', 'Construction Corp',
            'Logistics Network', 'Media Productions', 'Security Systems'
        ]
        
        first_names = [
            'Maria', 'Juan', 'Ana', 'Jose', 'Carmen', 'Miguel', 'Sofia', 'Carlos',
            'Isabella', 'Diego', 'Lucia', 'Antonio', 'Gabriela', 'Francisco',
            'Valentina', 'Roberto', 'Camila', 'Alejandro', 'Natalia', 'Fernando'
        ]
        
        last_names = [
            'Garcia', 'Rodriguez', 'Martinez', 'Lopez', 'Gonzalez', 'Perez',
            'Sanchez', 'Ramirez', 'Cruz', 'Torres', 'Flores', 'Gomez',
            'Morales', 'Jimenez', 'Hernandez', 'Vargas', 'Castillo', 'Ruiz'
        ]
        
        job_titles = [
            'CEO', 'CTO', 'VP of Technology', 'IT Director', 'Operations Manager',
            'Project Manager', 'Business Analyst', 'Sales Director', 'Marketing Manager',
            'Finance Manager', 'Procurement Manager', 'General Manager'
        ]
        
        industries = [
            'technology', 'financial', 'healthcare', 'manufacturing',
            'education', 'government', 'energy', 'retail', 'hospitality', 'construction'
        ]
        
        territories = [
            'makati', 'manila', 'quezoncity', 'pasig', 'taguig', 
            'mandaluyong', 'paranaque', 'outsidencr'
        ]
        
        company_sizes = ['11-50', '51-200', '201-500', '501-1000', '1000+']
        annual_revenues = ['1m_5m', '5m_10m', '10m_50m', '50m_100m', 'over_100m']
        budget_ranges = ['10k_50k', '50k_100k', '100k_500k', '500k_1m', 'over_1m']
        timelines = ['immediate', 'short_term', 'medium_term', 'long_term']
        
        created_leads = 0
        
        for i in range(count):
            # Generate random lead data
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            company = random.choice(companies)
            
            lead_data = {
                'first_name': first_name,
                'last_name': last_name,
                'email': f'{first_name.lower()}.{last_name.lower()}@{company.lower().replace(" ", "").replace(",", "")}.com',
                'phone_number': f'+63-2-{random.randint(100, 999)}-{random.randint(1000, 9999)}',
                'company_name': company,
                'job_title': random.choice(job_titles),
                'industry': random.choice(industries),
                'territory': random.choice(territories),
                'source': random.choice(lead_sources),
                'assigned_to': random.choice(users),
                'company_size': random.choice(company_sizes),
                'annual_revenue': random.choice(annual_revenues),
                'budget_range': random.choice(budget_ranges),
                'timeline': random.choice(timelines),
                'notes': f'Generated sample lead for {company}. Interested in our solutions.',
            }
            
            # Create the lead
            lead = Lead.objects.create(**lead_data)
            created_leads += 1
            
            # Add some random activities
            self._create_sample_activities(lead)
            
            if i % 5 == 0:
                self.stdout.write(f'Created {i + 1} leads...')
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_leads} sample leads'))
        
        # Score all leads using the scoring engine
        self.stdout.write('Calculating lead scores...')
        scoring_engine = LeadScoringEngine()
        
        scored_count = 0
        for lead in Lead.objects.all():
            scoring_engine.calculate_lead_score(lead)
            scored_count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Scored {scored_count} leads'))
        
        # Display statistics
        self._display_statistics()

    def _create_sample_activities(self, lead):
        """Create sample activities for a lead"""
        
        activity_types = ['call', 'email', 'meeting', 'demo', 'follow_up', 'proposal']
        outcomes = [
            'successful', 'interested', 'not_interested', 'no_response', 
            'meeting_scheduled', 'proposal_requested', 'follow_up_needed'
        ]
        
        # Create 1-5 activities per lead
        num_activities = random.randint(1, 5)
        
        for i in range(num_activities):
            days_ago = random.randint(1, 30)
            activity_date = timezone.now() - timedelta(days=days_ago)
            
            activity_data = {
                'lead': lead,
                'activity_type': random.choice(activity_types),
                'outcome': random.choice(outcomes),
                'notes': f'Sample activity {i + 1} - {random.choice(["Follow-up call", "Email response", "Product demo", "Meeting discussion", "Proposal review"])}',
                'created_by': lead.assigned_to,
                'activity_date': activity_date,
                'created_at': activity_date
            }
            
            LeadActivity.objects.create(**activity_data)

    def _display_statistics(self):
        """Display statistics about the created leads"""
        
        total_leads = Lead.objects.count()
        hot_leads = Lead.objects.filter(lead_score__gte=75).count()
        qualified_leads = Lead.objects.filter(is_qualified=True).count()
        high_priority = Lead.objects.filter(priority='high').count()
        
        avg_score = Lead.objects.aggregate(
            avg_score=models.Avg('lead_score')
        )['avg_score'] or 0
        
        self.stdout.write(self.style.SUCCESS('\n📊 Lead Generation Statistics:'))
        self.stdout.write(f'   Total Leads: {total_leads}')
        self.stdout.write(f'   Hot Leads (≥75 points): {hot_leads}')
        self.stdout.write(f'   Qualified Leads: {qualified_leads}')
        self.stdout.write(f'   High Priority Leads: {high_priority}')
        self.stdout.write(f'   Average Score: {avg_score:.1f}')
        
        # Score distribution
        score_ranges = [
            ('Hot Leads (75-100)', Lead.objects.filter(lead_score__gte=75).count()),
            ('Warm Leads (50-74)', Lead.objects.filter(lead_score__gte=50, lead_score__lt=75).count()),
            ('Cold Leads (25-49)', Lead.objects.filter(lead_score__gte=25, lead_score__lt=50).count()),
            ('Poor Leads (0-24)', Lead.objects.filter(lead_score__lt=25).count()),
        ]
        
        self.stdout.write(self.style.WARNING('\n🌡️  Score Distribution:'))
        for range_name, count in score_ranges:
            percentage = (count / total_leads * 100) if total_leads > 0 else 0
            self.stdout.write(f'   {range_name}: {count} ({percentage:.1f}%)')
        
        # Top scoring leads
        top_leads = Lead.objects.order_by('-lead_score')[:5]
        self.stdout.write(self.style.WARNING('\n🏆 Top 5 Scoring Leads:'))
        for lead in top_leads:
            self.stdout.write(f'   • {lead.get_full_name()} ({lead.company_name}): {lead.lead_score} pts')
        
        self.stdout.write(self.style.SUCCESS('\n✅ Sample lead data created and scored successfully!'))
        self.stdout.write(self.style.WARNING('🔍 You can now test the lead generation features:'))
        self.stdout.write('   • Visit /leads/dashboard/ to see the lead dashboard')
        self.stdout.write('   • Visit /leads/ to see all leads with scores')
        self.stdout.write('   • Visit /leads/hot/ to see hot leads')
        self.stdout.write('   • Visit /admin/ to manage scoring rules')
