
import os
import django
import glob
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest.mock import Mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_proposals.views import proposal_email
from sales_proposals.models import Proposal, ProposalItem
from users.models import User
from customers.models import Customer
from teams.models import Group, Team, TeamMembership

def test_email_options():
    print("Setting up test data...")
    # Create Supervisor
    supervisor, _ = User.objects.get_or_create(username='boss_man', email='boss@micrm.com', role='supervisor')
    if not supervisor.check_password('password'):
        supervisor.set_password('password')
        supervisor.save()
        
    # Create Team/Group
    team, _ = Team.objects.get_or_create(name="Test Team")
    group, _ = Group.objects.get_or_create(name="Test Group", team=team, supervisor=supervisor)
    
    # Create Salesperson
    salesperson, _ = User.objects.get_or_create(username='sales_rep', email='rep@micrm.com', role='salesperson')
    if not salesperson.check_password('password'):
        salesperson.set_password('password')
        salesperson.save()
        
    # Assign salesperson to group
    TeamMembership.objects.get_or_create(user=salesperson, group=group)
        
    customer = Customer.objects.filter(email='original@client.com').first()
    if not customer:
        customer = Customer.objects.create(company_name='Client Corp', contact_person_name='Mr. Client', email='original@client.com')
    
    import random
    unique_id = random.randint(10000, 99999)
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=salesperson,
        subject="Test Options Email",
        date=timezone.now().date(),
        status='draft',
        proposal_number=f"TEST-OPT-{unique_id}"
    )
    
    ProposalItem.objects.create(proposal=proposal, description="Item", quantity=1, unit_price=100, unit_cost=50)
    proposal.calculate_totals()
    
    # Simulate POST request with options
    factory = RequestFactory()
    
    # Test changing email and CCing supervisor
    new_email = "updated@client.com"
    data = {
        'customer_email': new_email,
        'cc_supervisor': 'on'
    }
    
    request = factory.post(f'/proposals/{proposal.pk}/email/', data=data)
    request.user = salesperson
    
    # Add messages support
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    print(f"Sending email... To: {new_email}, CC: Supervisor")
    try:
        response = proposal_email(request, pk=proposal.pk)
        
        # Check if email file was created
        email_files = glob.glob('sent_emails/*.log')
        if email_files:
            latest_email = max(email_files, key=os.path.getctime)
            print(f"Email file found: {latest_email}")
            with open(latest_email, 'r') as f:
                content = f.read()
                print("\n--- Email Checks ---")
                
                # Check To
                if f"To: {new_email}" in content:
                    print(f"SUCCESS: 'To' changed to {new_email}")
                else:
                    print(f"FAILURE: 'To' header incorrect.")
                    
                # Check CC
                if f"Cc: {supervisor.email}" in content:
                    print(f"SUCCESS: 'Cc' includes supervisor {supervisor.email}")
                else:
                    print(f"FAILURE: 'Cc' header missing supervisor.")
                    
        else:
            print("FAILURE: No email file found.")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_email_options()
