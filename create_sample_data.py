#!/usr/bin/env python
"""
Sample data creation script for Executive CRM Dashboard testing
"""
import os
import sys
import django
from decimal import Decimal
from datetime import datetime, timedelta, date
import random

# Add the project root to Python path
sys.path.append('/home/greg/projects/crm_project')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from users.models import User
from teams.models import Team, Group, TeamMembership
from customers.models import Customer
from sales_funnel.models import SalesFunnel
from sales_monitoring.models import SalesActivity, ActivityType

def create_sample_users():
    """Create sample users for testing"""
    print("Creating sample users...")
    
    # Create VP
    vp_user, created = User.objects.get_or_create(
        username='vp_john',
        defaults={
            'first_name': 'John',
            'last_name': 'VP',
            'email': 'vp@company.com',
            'role': 'vp',
            'is_active': True
        }
    )
    if created:
        vp_user.set_password('password123')
        vp_user.save()
    
    # Create AVPs
    avp1, created = User.objects.get_or_create(
        username='avp_alice',
        defaults={
            'first_name': 'Alice',
            'last_name': 'AVP',
            'email': 'avp1@company.com',
            'role': 'avp',
            'is_active': True
        }
    )
    if created:
        avp1.set_password('password123')
        avp1.save()
    
    avp2, created = User.objects.get_or_create(
        username='avp_bob',
        defaults={
            'first_name': 'Bob',
            'last_name': 'AVP',
            'email': 'avp2@company.com',
            'role': 'avp',
            'is_active': True
        }
    )
    if created:
        avp2.set_password('password123')
        avp2.save()
    
    # Create Supervisors
    supervisor1, created = User.objects.get_or_create(
        username='sup_carol',
        defaults={
            'first_name': 'Carol',
            'last_name': 'Supervisor',
            'email': 'sup1@company.com',
            'role': 'supervisor',
            'is_active': True
        }
    )
    if created:
        supervisor1.set_password('password123')
        supervisor1.save()
    
    supervisor2, created = User.objects.get_or_create(
        username='sup_dave',
        defaults={
            'first_name': 'Dave',
            'last_name': 'Supervisor',
            'email': 'sup2@company.com',
            'role': 'supervisor',
            'is_active': True
        }
    )
    if created:
        supervisor2.set_password('password123')
        supervisor2.save()
    
    # Create Salespeople
    salespeople = []
    sales_names = [
        ('Emma', 'Johnson'), ('Michael', 'Smith'), ('Sarah', 'Davis'),
        ('James', 'Wilson'), ('Lisa', 'Brown'), ('David', 'Taylor'),
        ('Anna', 'Miller'), ('Chris', 'Anderson'), ('Jennifer', 'Garcia')
    ]
    
    for i, (first, last) in enumerate(sales_names):
        username = f'sales_{first.lower()}'
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'first_name': first,
                'last_name': last,
                'email': f'{username}@company.com',
                'role': 'salesperson',
                'is_active': True,
                'initials': f'{first[0]}{last[0]}{str(i+1)}'
            }
        )
        if created:
            user.set_password('password123')
            user.save()
        salespeople.append(user)
    
    return vp_user, avp1, avp2, supervisor1, supervisor2, salespeople

def create_sample_teams_and_groups(avp1, avp2, supervisor1, supervisor2, salespeople):
    """Create sample teams and groups"""
    print("Creating sample teams and groups...")
    
    # Create Teams
    team1, created = Team.objects.get_or_create(
        name='Enterprise Sales Team',
        defaults={'avp': avp1}
    )
    
    team2, created = Team.objects.get_or_create(
        name='SMB Sales Team',
        defaults={'avp': avp2}
    )
    
    # Create Groups
    group1, created = Group.objects.get_or_create(
        name='Enterprise Group A',
        defaults={
            'team': team1,
            'group_type': 'regular',
            'supervisor': supervisor1
        }
    )
    
    group2, created = Group.objects.get_or_create(
        name='Enterprise Group B',
        defaults={
            'team': team1,
            'group_type': 'regular',
            'supervisor': supervisor2
        }
    )
    
    group3, created = Group.objects.get_or_create(
        name='Technical Sales Group',
        defaults={
            'team': team2,
            'group_type': 'tsg',
            'supervisor': None  # TSG groups don't have supervisors
        }
    )
    
    # Assign salespeople to groups
    groups = [group1, group2, group3]
    for i, salesperson in enumerate(salespeople):
        group = groups[i % len(groups)]
        membership, created = TeamMembership.objects.get_or_create(
            user=salesperson,
            defaults={'group': group}
        )
    
    return [group1, group2, group3]

def create_sample_customers_and_deals(salespeople):
    """Create sample customers and sales funnel entries"""
    print("Creating sample customers and deals...")
    
    companies = [
        'Tech Solutions Inc', 'Global Manufacturing Corp', 'Digital Services Ltd',
        'Healthcare Systems', 'Financial Partners', 'Retail Giants',
        'Construction Masters', 'Education Network', 'Transport Logistics',
        'Energy Solutions', 'Food & Beverage Co', 'Real Estate Group'
    ]
    
    customers = []
    for i, company_name in enumerate(companies):
        customer, created = Customer.objects.get_or_create(
            company_name=company_name,
            defaults={
                'contact_person_name': f'Contact Person {i+1}',
                'email': f'contact{i+1}@{company_name.lower().replace(" ", "").replace("&", "")}.com',
                'phone_number': f'+63915555{1000+i}',
                'industry': random.choice(['technology', 'manufacturing', 'healthcare', 'financial', 'retail']),
                'territory': random.choice(['makati', 'bgc', 'ortigas', 'manila', 'quezoncity']),
                'is_active': True,
                'salesperson': random.choice(salespeople)
            }
        )
        customers.append(customer)
    
    # Create sales funnel entries
    stages = ['quoted', 'closable', 'project']
    outcomes = ['active', 'won', 'lost']
    
    for i in range(30):  # Create 30 sample deals
        cost = Decimal(random.randint(10000, 500000))
        retail = cost * Decimal(random.uniform(1.2, 2.5))  # 20% to 150% markup
        
        # Create dates - some current month, some previous months
        months_back = random.randint(0, 6)
        deal_date = date.today() - timedelta(days=months_back * 30)
        
        # Determine outcome based on age
        if months_back > 3:
            outcome = random.choice(['won', 'lost'])
            is_closed = True
            closed_date = deal_date + timedelta(days=random.randint(7, 60))
        else:
            outcome = 'active'
            is_closed = False
            closed_date = None
        
        SalesFunnel.objects.get_or_create(
            company_name=f"Deal Company {i+1}",
            defaults={
                'date_created': deal_date,
                'requirement_description': f'Sample requirement description for deal {i+1}',
                'cost': cost,
                'retail': retail,
                'stage': random.choice(stages),
                'salesperson': random.choice(salespeople),
                'customer': random.choice(customers) if random.random() > 0.3 else None,
                'expected_close_date': deal_date + timedelta(days=random.randint(30, 90)),
                'probability': random.randint(20, 90),
                'is_active': not is_closed,
                'is_closed': is_closed,
                'deal_outcome': outcome,
                'closed_date': closed_date,
                'notes': f'Sample notes for deal {i+1}'
            }
        )

def create_sample_activities(salespeople):
    """Create sample sales activities"""
    print("Creating sample sales activities...")
    
    # Ensure activity types exist
    activity_types = [
        ('Call', 'Phone calls to prospects and customers', 'fas fa-phone', 'primary'),
        ('Meeting', 'Face-to-face or virtual meetings', 'fas fa-handshake', 'success'),
        ('Email', 'Email communications', 'fas fa-envelope', 'info'),
        ('Proposal', 'Proposal creation and presentation', 'fas fa-file-contract', 'warning'),
        ('Follow-up', 'Follow-up activities', 'fas fa-redo', 'secondary'),
    ]
    
    for name, desc, icon, color in activity_types:
        ActivityType.objects.get_or_create(
            name=name,
            defaults={
                'description': desc,
                'icon': icon,
                'color': color,
                'is_active': True
            }
        )
    
    # Create activities for the last 30 days
    activity_types_qs = ActivityType.objects.filter(is_active=True)
    statuses = ['planned', 'in_progress', 'completed', 'cancelled']
    priorities = ['low', 'medium', 'high', 'urgent']
    
    for i in range(100):  # Create 100 sample activities
        days_back = random.randint(0, 30)
        activity_date = datetime.now() - timedelta(days=days_back)
        
        # Determine status based on age
        if days_back > 7:
            status = random.choice(['completed', 'cancelled'])
        else:
            status = random.choice(['planned', 'in_progress', 'completed'])
        
        SalesActivity.objects.get_or_create(
            title=f'Sample Activity {i+1}',
            defaults={
                'description': f'Sample description for activity {i+1}',
                'activity_type': random.choice(activity_types_qs),
                'salesperson': random.choice(salespeople),
                'status': status,
                'priority': random.choice(priorities),
                'scheduled_start': activity_date,
                'scheduled_end': activity_date + timedelta(hours=random.randint(1, 4)),
                'actual_start': activity_date if status in ['completed', 'cancelled'] else None,
                'actual_end': activity_date + timedelta(hours=random.randint(1, 4)) if status == 'completed' else None,
                'notes': f'Sample notes for activity {i+1}',
                'follow_up_required': random.choice([True, False]),
                'reviewed_by_supervisor': random.choice([True, False]) if status == 'completed' else False
            }
        )

def main():
    """Main function to create all sample data"""
    print("Starting sample data creation for Executive CRM Dashboard...")
    
    # Create users
    vp_user, avp1, avp2, supervisor1, supervisor2, salespeople = create_sample_users()
    
    # Create teams and groups
    groups = create_sample_teams_and_groups(avp1, avp2, supervisor1, supervisor2, salespeople)
    
    # Create customers and deals
    create_sample_customers_and_deals(salespeople)
    
    # Create activities
    create_sample_activities(salespeople)
    
    print("\n" + "="*60)
    print("Sample data creation completed!")
    print("="*60)
    print("\nExecutive Dashboard Test Accounts:")
    print(f"VP Account: username='vp_john', password='password123'")
    print(f"AVP Account: username='avp_alice', password='password123'")
    print(f"Supervisor Account: username='sup_carol', password='password123'")
    print(f"Salesperson Account: username='sales_emma', password='password123'")
    print("\nAccess the Executive Dashboard at:")
    print("http://127.0.0.1:8000/sales-monitoring/executive/")
    print("\n" + "="*60)

if __name__ == '__main__':
    main()
