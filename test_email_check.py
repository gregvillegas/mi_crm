
import os
import django
import glob
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from unittest.mock import MagicMock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_proposals.views import proposal_email
from sales_proposals.models import Proposal, ProposalItem
from users.models import User
from customers.models import Customer
from sales_funnel.models import SalesFunnel

def test_email_sending():
    print("Setting up test data...")
    user, _ = User.objects.get_or_create(username='email_tester', email='tester@micrm.com', role='salesperson')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()
        
    customer = Customer.objects.filter(email='greg.villegas@gmail.com').first()
    if not customer:
        customer = Customer.objects.create(company_name='Email Test Corp', contact_person_name='Email Tester', email='greg.villegas@gmail.com')
    
    # Clean up previous proposals/funnels for this test customer
    Proposal.objects.filter(customer=customer).delete()
    SalesFunnel.objects.filter(customer=customer).delete()

    import random
    unique_id = random.randint(10000, 99999)
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Test Proposal Email",
        date=timezone.now().date(),
        status='draft',
        proposal_number=f"TEST-{unique_id}"
    )
    
    ProposalItem.objects.create(
        proposal=proposal,
        description="Test Item",
        quantity=1,
        unit_price=1000,
        unit_cost=500
    )
    proposal.calculate_totals()
    
    # Simulate a POST request to send email
    factory = RequestFactory()
    request = factory.post(f'/proposals/{proposal.pk}/email/')
    request.user = user
    
    # Add messages support to request
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    print("Sending email via view...")
    try:
        response = proposal_email(request, pk=proposal.pk)
        print(f"Response status code: {response.status_code}")
        
        # Check if email file was created
        email_files = glob.glob('sent_emails/*.log')
        if email_files:
            latest_email = max(email_files, key=os.path.getctime)
            print(f"Email file found: {latest_email}")
            with open(latest_email, 'r') as f:
                content = f.read()
                print("\n--- Email Content Preview ---")
                print(content[:500] + "...") # Print first 500 chars
                if "To: greg.villegas@gmail.com" in content:
                    print("\nSUCCESS: Email addressed correctly.")
                else:
                    print("\nFAILURE: Email address not found in content.")
        else:
            print("FAILURE: No email file found in sent_emails directory.")
            
    except Exception as e:
        print(f"Error during email sending: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_email_sending()
