
import os
import django
import glob
from django.utils import timezone
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_proposals.views import proposal_email
from sales_proposals.models import Proposal, ProposalItem
from users.models import User
from customers.models import Customer
from sales_funnel.models import SalesFunnel

def test_sender_email():
    print("Setting up test data...")
    # Create a user with a specific email
    sender_email = 'salesperson_jane@micrm.com'
    user, _ = User.objects.get_or_create(username='jane_doe', email=sender_email, role='salesperson')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()
        
    customer = Customer.objects.filter(email='client@example.com').first()
    if not customer:
        customer = Customer.objects.create(company_name='Client Corp', contact_person_name='Mr. Client', email='client@example.com')
    
    # Clean up previous proposals/funnels for this test customer
    Proposal.objects.filter(customer=customer).delete()
    SalesFunnel.objects.filter(customer=customer).delete()

    import random
    unique_id = random.randint(10000, 99999)
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Test Sender Email",
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
    request.user = user # This is the crucial part - logged in user
    
    # Add messages support to request
    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)
    
    print(f"Sending email as user: {user.email}...")
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
                print("\n--- Email Headers Check ---")
                # Simple check for From header
                if f"From: {sender_email}" in content:
                    print(f"SUCCESS: 'From' header matches user email: {sender_email}")
                else:
                    print(f"FAILURE: 'From' header does not match. Content excerpt:\n{content[:300]}")
                    
                if f"Reply-To: {sender_email}" in content:
                     print(f"SUCCESS: 'Reply-To' header matches user email.")
        else:
            print("FAILURE: No email file found in sent_emails directory.")
            
    except Exception as e:
        print(f"Error during email sending: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_sender_email()
