
import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_proposals.models import Proposal, ProposalItem
from customers.models import Customer
from users.models import User

def test_long_description():
    print("Testing long description...")
    
    # Create dummy user and customer
    username = f"test_user_{timezone.now().timestamp()}"
    user, _ = User.objects.get_or_create(username=username, email=f"{username}@example.com", role='salesperson')
    customer, _ = Customer.objects.get_or_create(company_name="Test Company", email="test@example.com", salesperson=user)
    
    # Create proposal
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Test Proposal for Long Description",
        subtotal=1000,
        total_amount=1120
    )
    
    # Create item with long description (> 255 chars)
    long_desc = "A" * 300
    item = ProposalItem.objects.create(
        proposal=proposal,
        description=long_desc,
        unit_price=1000,
        quantity=1
    )
    
    # Verify
    saved_item = ProposalItem.objects.get(id=item.id)
    if len(saved_item.description) == 300:
        print("SUCCESS: ProposalItem saved with 300 characters description.")
    else:
        print(f"FAILURE: Description length is {len(saved_item.description)}")

    # Cleanup
    proposal.delete()
    customer.delete()
    user.delete()

if __name__ == "__main__":
    test_long_description()
