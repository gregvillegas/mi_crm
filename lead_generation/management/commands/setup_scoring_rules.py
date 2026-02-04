from django.core.management.base import BaseCommand
from django.db import transaction
from lead_generation.scoring_models import (
    ScoringCriteria, ScoringRule, LeadScoringProfile, 
    ActivityScoringRule, ProfileCriteria
)

class Command(BaseCommand):
    help = 'Set up automated lead scoring rules and system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset all existing scoring rules and create fresh ones',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write('Resetting all scoring rules...')
            ScoringRule.objects.all().delete()
            ActivityScoringRule.objects.all().delete()
            ScoringCriteria.objects.all().delete()
            LeadScoringProfile.objects.all().delete()

        with transaction.atomic():
            # Create default scoring profile
            profile, created = LeadScoringProfile.objects.get_or_create(
                name="Standard Lead Scoring",
                defaults={
                    'description': 'Standard lead scoring profile with comprehensive criteria',
                    'is_default': True,
                    'auto_assign_threshold': 80,
                    'hot_lead_threshold': 75
                }
            )
            
            if created:
                self.stdout.write(self.style.SUCCESS('Created default scoring profile'))
            
            # Create scoring criteria
            criteria_list = [
                {
                    'name': 'Company Size',
                    'criteria_type': 'firmographic',
                    'description': 'Score based on number of employees',
                    'weight': 1.5,
                    'max_score': 25
                },
                {
                    'name': 'Annual Revenue',
                    'criteria_type': 'firmographic',
                    'description': 'Score based on company annual revenue',
                    'weight': 2.0,
                    'max_score': 25
                },
                {
                    'name': 'Budget Range',
                    'criteria_type': 'demographic',
                    'description': 'Score based on available budget for purchase',
                    'weight': 2.0,
                    'max_score': 20
                },
                {
                    'name': 'Timeline Urgency',
                    'criteria_type': 'temporal',
                    'description': 'Score based on purchase timeline urgency',
                    'weight': 1.5,
                    'max_score': 15
                },
                {
                    'name': 'Lead Source Quality',
                    'criteria_type': 'source',
                    'description': 'Score based on lead source conversion rate',
                    'weight': 1.0,
                    'max_score': 10
                },
                {
                    'name': 'Profile Completeness',
                    'criteria_type': 'demographic',
                    'description': 'Score based on profile information completeness',
                    'weight': 0.8,
                    'max_score': 10
                },
                {
                    'name': 'Industry Match',
                    'criteria_type': 'firmographic',
                    'description': 'Score based on industry sector alignment',
                    'weight': 1.2,
                    'max_score': 15
                },
                {
                    'name': 'Geographic Fit',
                    'criteria_type': 'demographic',
                    'description': 'Score based on territory and location',
                    'weight': 0.8,
                    'max_score': 10
                }
            ]
            
            created_criteria = 0
            for criteria_data in criteria_list:
                criteria, created = ScoringCriteria.objects.get_or_create(
                    name=criteria_data['name'],
                    defaults=criteria_data
                )
                
                if created:
                    created_criteria += 1
                    self.stdout.write(f'Created criteria: {criteria.name}')
                    
                    # Associate with profile
                    ProfileCriteria.objects.get_or_create(
                        profile=profile,
                        criteria=criteria,
                        defaults={
                            'weight_multiplier': 1.0,
                            'is_enabled': True
                        }
                    )
            
            self.stdout.write(self.style.SUCCESS(f'Created {created_criteria} scoring criteria'))
            
            # Create detailed scoring rules
            self._create_scoring_rules()
            
            # Create activity scoring rules
            self._create_activity_scoring_rules()
            
            self.stdout.write(self.style.SUCCESS('✅ Automated lead scoring system set up successfully!'))
            self.stdout.write(self.style.WARNING('📋 Scoring Criteria Created:'))
            for criteria in ScoringCriteria.objects.all():
                rule_count = criteria.rules.count()
                self.stdout.write(f'   • {criteria.name}: {rule_count} rules (max {criteria.max_score} pts, weight {criteria.weight})')

    def _create_scoring_rules(self):
        """Create detailed scoring rules for each criteria"""
        
        rules_data = [
            # Company Size Rules
            {
                'criteria_name': 'Company Size',
                'rules': [
                    {'field_name': 'company_size', 'operator': 'eq', 'value': '"1000+"', 'points': 25, 'description': '1000+ employees'},
                    {'field_name': 'company_size', 'operator': 'eq', 'value': '"501-1000"', 'points': 20, 'description': '501-1000 employees'},
                    {'field_name': 'company_size', 'operator': 'eq', 'value': '"201-500"', 'points': 15, 'description': '201-500 employees'},
                    {'field_name': 'company_size', 'operator': 'eq', 'value': '"51-200"', 'points': 10, 'description': '51-200 employees'},
                    {'field_name': 'company_size', 'operator': 'eq', 'value': '"11-50"', 'points': 5, 'description': '11-50 employees'},
                ]
            },
            # Annual Revenue Rules
            {
                'criteria_name': 'Annual Revenue',
                'rules': [
                    {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"over_100m"', 'points': 25, 'description': 'Over $100M revenue'},
                    {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"50m_100m"', 'points': 20, 'description': '$50M-$100M revenue'},
                    {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"10m_50m"', 'points': 15, 'description': '$10M-$50M revenue'},
                    {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"5m_10m"', 'points': 10, 'description': '$5M-$10M revenue'},
                    {'field_name': 'annual_revenue', 'operator': 'eq', 'value': '"1m_5m"', 'points': 5, 'description': '$1M-$5M revenue'},
                ]
            },
            # Budget Range Rules
            {
                'criteria_name': 'Budget Range',
                'rules': [
                    {'field_name': 'budget_range', 'operator': 'eq', 'value': '"over_1m"', 'points': 20, 'description': 'Over $1M budget'},
                    {'field_name': 'budget_range', 'operator': 'eq', 'value': '"500k_1m"', 'points': 15, 'description': '$500K-$1M budget'},
                    {'field_name': 'budget_range', 'operator': 'eq', 'value': '"100k_500k"', 'points': 12, 'description': '$100K-$500K budget'},
                    {'field_name': 'budget_range', 'operator': 'eq', 'value': '"50k_100k"', 'points': 8, 'description': '$50K-$100K budget'},
                    {'field_name': 'budget_range', 'operator': 'eq', 'value': '"10k_50k"', 'points': 5, 'description': '$10K-$50K budget'},
                ]
            },
            # Timeline Rules
            {
                'criteria_name': 'Timeline Urgency',
                'rules': [
                    {'field_name': 'timeline', 'operator': 'eq', 'value': '"immediate"', 'points': 15, 'description': 'Immediate timeline'},
                    {'field_name': 'timeline', 'operator': 'eq', 'value': '"short_term"', 'points': 12, 'description': 'Short term (1-3 months)'},
                    {'field_name': 'timeline', 'operator': 'eq', 'value': '"medium_term"', 'points': 8, 'description': 'Medium term (3-6 months)'},
                    {'field_name': 'timeline', 'operator': 'eq', 'value': '"long_term"', 'points': 4, 'description': 'Long term (6+ months)'},
                ]
            },
            # Profile Completeness Rules
            {
                'criteria_name': 'Profile Completeness',
                'rules': [
                    {'field_name': 'phone_number', 'operator': 'is_not_null', 'value': '""', 'points': 2, 'description': 'Phone number provided'},
                    {'field_name': 'company_name', 'operator': 'is_not_null', 'value': '""', 'points': 2, 'description': 'Company name provided'},
                    {'field_name': 'job_title', 'operator': 'is_not_null', 'value': '""', 'points': 2, 'description': 'Job title provided'},
                    {'field_name': 'industry', 'operator': 'is_not_null', 'value': '""', 'points': 2, 'description': 'Industry specified'},
                    {'field_name': 'territory', 'operator': 'is_not_null', 'value': '""', 'points': 2, 'description': 'Territory specified'},
                ]
            },
            # Industry Match Rules
            {
                'criteria_name': 'Industry Match',
                'rules': [
                    {'field_name': 'industry', 'operator': 'in', 'value': '["technology", "financial", "healthcare", "manufacturing"]', 'points': 15, 'description': 'High-value industries'},
                    {'field_name': 'industry', 'operator': 'in', 'value': '["education", "government", "energy"]', 'points': 10, 'description': 'Medium-value industries'},
                    {'field_name': 'industry', 'operator': 'in', 'value': '["retail", "hospitality", "construction"]', 'points': 5, 'description': 'Standard industries'},
                ]
            },
            # Geographic Fit Rules
            {
                'criteria_name': 'Geographic Fit',
                'rules': [
                    {'field_name': 'territory', 'operator': 'in', 'value': '["makati", "manila", "quezoncity", "pasig"]', 'points': 10, 'description': 'Prime NCR locations'},
                    {'field_name': 'territory', 'operator': 'in', 'value': '["taguig", "mandaluyong", "paranaque"]', 'points': 8, 'description': 'Good NCR locations'},
                    {'field_name': 'territory', 'operator': 'eq', 'value': '"outsidencr"', 'points': 3, 'description': 'Outside NCR'},
                ]
            },
        ]
        
        created_rules = 0
        for criteria_rules in rules_data:
            try:
                criteria = ScoringCriteria.objects.get(name=criteria_rules['criteria_name'])
                
                for rule_data in criteria_rules['rules']:
                    rule, created = ScoringRule.objects.get_or_create(
                        criteria=criteria,
                        field_name=rule_data['field_name'],
                        operator=rule_data['operator'],
                        value=rule_data['value'],
                        defaults={
                            'points': rule_data['points'],
                            'description': rule_data['description']
                        }
                    )
                    
                    if created:
                        created_rules += 1
                        
            except ScoringCriteria.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Criteria not found: {criteria_rules["criteria_name"]}')
                )
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_rules} scoring rules'))

    def _create_activity_scoring_rules(self):
        """Create activity-based scoring rules"""
        
        activity_rules = [
            {
                'name': 'Successful Phone Call',
                'activity_type': 'call',
                'outcome': 'successful',
                'points_per_activity': 10,
                'max_points_per_day': 30,
                'decay_days': 30,
                'decay_rate': 0.10
            },
            {
                'name': 'Meeting Scheduled',
                'activity_type': '',
                'outcome': 'meeting_scheduled',
                'points_per_activity': 15,
                'max_points_per_day': 45,
                'decay_days': 21,
                'decay_rate': 0.05
            },
            {
                'name': 'Showed Interest',
                'activity_type': '',
                'outcome': 'interested',
                'points_per_activity': 12,
                'max_points_per_day': 36,
                'decay_days': 14,
                'decay_rate': 0.15
            },
            {
                'name': 'Proposal Requested',
                'activity_type': '',
                'outcome': 'proposal_requested',
                'points_per_activity': 25,
                'max_points_per_day': 75,
                'decay_days': 45,
                'decay_rate': 0.03
            },
            {
                'name': 'Demo Conducted',
                'activity_type': 'demo',
                'outcome': 'successful',
                'points_per_activity': 20,
                'max_points_per_day': 60,
                'decay_days': 30,
                'decay_rate': 0.08
            },
            {
                'name': 'Email Response',
                'activity_type': 'email',
                'outcome': 'interested',
                'points_per_activity': 8,
                'max_points_per_day': 24,
                'decay_days': 7,
                'decay_rate': 0.20
            },
            {
                'name': 'Follow-up Call',
                'activity_type': 'follow_up',
                'outcome': 'successful',
                'points_per_activity': 7,
                'max_points_per_day': 21,
                'decay_days': 14,
                'decay_rate': 0.12
            },
            {
                'name': 'Meeting Attended',
                'activity_type': 'meeting',
                'outcome': 'successful',
                'points_per_activity': 18,
                'max_points_per_day': 54,
                'decay_days': 30,
                'decay_rate': 0.06
            },
            {
                'name': 'Proposal Sent',
                'activity_type': 'proposal',
                'outcome': 'successful',
                'points_per_activity': 22,
                'max_points_per_day': 66,
                'decay_days': 60,
                'decay_rate': 0.02
            },
            {
                'name': 'No Response',
                'activity_type': '',
                'outcome': 'no_response',
                'points_per_activity': -2,
                'max_points_per_day': -6,
                'decay_days': 7,
                'decay_rate': 0.30
            },
            {
                'name': 'Not Interested',
                'activity_type': '',
                'outcome': 'not_interested',
                'points_per_activity': -10,
                'max_points_per_day': -30,
                'decay_days': 0,
                'decay_rate': 0.00
            }
        ]
        
        created_activity_rules = 0
        for rule_data in activity_rules:
            rule, created = ActivityScoringRule.objects.get_or_create(
                name=rule_data['name'],
                defaults=rule_data
            )
            
            if created:
                created_activity_rules += 1
                self.stdout.write(f'Created activity rule: {rule.name}')
        
        self.stdout.write(self.style.SUCCESS(f'Created {created_activity_rules} activity scoring rules'))
        
        # Display summary
        self.stdout.write(self.style.SUCCESS('\n🎯 Automated Lead Scoring System Setup Complete!'))
        self.stdout.write(self.style.WARNING('\n📊 Scoring Breakdown:'))
        self.stdout.write('• Company Size: 0-25 points (weight: 1.5x)')
        self.stdout.write('• Annual Revenue: 0-25 points (weight: 2.0x)')
        self.stdout.write('• Budget Range: 0-20 points (weight: 2.0x)')
        self.stdout.write('• Timeline Urgency: 0-15 points (weight: 1.5x)')
        self.stdout.write('• Industry Match: 0-15 points (weight: 1.2x)')
        self.stdout.write('• Profile Completeness: 0-10 points (weight: 0.8x)')
        self.stdout.write('• Lead Source Quality: 0-10 points (weight: 1.0x)')
        self.stdout.write('• Geographic Fit: 0-10 points (weight: 0.8x)')
        
        self.stdout.write(self.style.WARNING('\n🚀 Automated Actions:'))
        self.stdout.write('• Leads ≥80 points: Marked as HOT, auto-assigned')
        self.stdout.write('• Leads ≥75 points: Generate hot lead alerts')
        self.stdout.write('• Leads ≥70 points: Automatically qualified')
        self.stdout.write('• Priority updated based on score ranges')
        self.stdout.write('• Follow-up scheduling based on urgency')
        
        self.stdout.write(self.style.WARNING('\n⚡ Activity Scoring:'))
        self.stdout.write('• Positive activities increase scores over time')
        self.stdout.write('• Negative activities decrease scores')
        self.stdout.write('• Time decay applied to older activities')
        self.stdout.write('• Recent engagement heavily weighted')
