
import os
import django
from decimal import Decimal
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from users.models import User
from customers.models import Customer
from sales_proposals.models import Proposal, ProposalItem
from sales_funnel.models import SalesFunnel
from sales_proposals.views import update_sales_funnel

def run_test():
    print("Setting up test data...")
    # Create User
    user, _ = User.objects.get_or_create(username='test_sales', email='test@example.com', role='salesperson')
    user.set_password('password')
    user.save()

    # Create Customer
    customer, _ = Customer.objects.get_or_create(company_name='Test Corp', contact_person_name='John Doe', email='john@test.com')

    # Cleanup existing funnel for this customer/user
    SalesFunnel.objects.filter(customer=customer, salesperson=user).delete()
    print("Cleaned up existing funnel entries.")

    # Create Proposal
    print("Creating proposal...")
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Test Proposal for Widget",
        date=timezone.now().date(),
        status='draft'
    )
    
    item = ProposalItem.objects.create(
        proposal=proposal,
        description="Widget X",
        quantity=10,
        unit_price=Decimal('1000.00'),
        unit_cost=Decimal('800.00')
    )
    
    proposal.calculate_totals()
    print(f"Proposal created: Total={proposal.total_amount}, Cost={proposal.total_cost}")

    # Manually call update_sales_funnel (as view would)
    print("Calling update_sales_funnel...")
    update_sales_funnel(proposal)

    # Check Funnel
    funnels = SalesFunnel.objects.filter(customer=customer, salesperson=user)
    print(f"Funnel entries found: {funnels.count()}")
    
    if funnels.exists():
        f = funnels.first()
        print(f"Entry: {f.company_name} - {f.stage} - Retail: {f.retail} - Cost: {f.cost}")
        
        if f.retail == proposal.total_amount and f.cost == proposal.total_cost:
            print("SUCCESS: Funnel entry matches proposal.")
        else:
            print("FAILURE: Funnel entry values do not match.")
    else:
        print("FAILURE: No funnel entry created.")

    # Test Update Scenario
    print("\nTesting Update Scenario (creating 2nd proposal for same customer)...")
    proposal2 = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Second Proposal",
        date=timezone.now().date(),
        status='draft'
    )
    item2 = ProposalItem.objects.create(
        proposal=proposal2,
        description="Widget Y",
        quantity=5,
        unit_price=Decimal('2000.00'), # 10000
        unit_cost=Decimal('1500.00')   # 7500
    )
    proposal2.calculate_totals()
    print(f"Proposal 2 created: Total={proposal2.total_amount}, Cost={proposal2.total_cost}")
    
    update_sales_funnel(proposal2)
    
    funnels = SalesFunnel.objects.filter(customer=customer, salesperson=user)
    print(f"Funnel entries found after 2nd proposal: {funnels.count()}")
    
    for f in funnels:
         print(f"Entry: {f.company_name} - {f.requirement_description} - Retail: {f.retail}")

if __name__ == '__main__':
    run_test()
