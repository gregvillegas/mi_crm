
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
    user, _ = User.objects.get_or_create(username='test_sales_v2', email='test2@example.com', role='salesperson')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()

    # Create Customer
    customer, _ = Customer.objects.get_or_create(company_name='Test Corp V2', contact_person_name='Jane Doe', email='jane@test.com')

    # Cleanup existing funnel for this customer/user
    SalesFunnel.objects.filter(customer=customer, salesperson=user).delete()
    Proposal.objects.filter(customer=customer, created_by=user).delete()
    print("Cleaned up existing data.")

    # Create Proposal 1
    print("Creating Proposal 1...")
    proposal1 = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Proposal 1",
        date=timezone.now().date(),
        status='draft'
    )
    ProposalItem.objects.create(proposal=proposal1, description="Item 1", quantity=1, unit_price=Decimal('1000'), unit_cost=Decimal('500'))
    proposal1.calculate_totals()
    
    update_sales_funnel(proposal1)
    
    funnels = SalesFunnel.objects.filter(customer=customer, salesperson=user)
    print(f"Funnel entries after Proposal 1: {funnels.count()}")
    if funnels.count() == 1:
        f = funnels.first()
        print(f"Entry 1: {f.requirement_description} - Linked Proposal ID: {f.proposal_id}")
        if f.proposal_id == proposal1.id:
            print("SUCCESS: Proposal 1 linked correctly.")
        else:
            print("FAILURE: Proposal 1 not linked.")

    # Create Proposal 2 (Same Customer)
    print("\nCreating Proposal 2...")
    proposal2 = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Proposal 2",
        date=timezone.now().date(),
        status='draft'
    )
    ProposalItem.objects.create(proposal=proposal2, description="Item 2", quantity=1, unit_price=Decimal('2000'), unit_cost=Decimal('1000'))
    proposal2.calculate_totals()
    
    update_sales_funnel(proposal2)
    
    funnels = SalesFunnel.objects.filter(customer=customer, salesperson=user)
    print(f"Funnel entries after Proposal 2: {funnels.count()}")
    
    if funnels.count() == 2:
        print("SUCCESS: Two distinct funnel entries created.")
        for f in funnels:
            print(f" - {f.requirement_description} (Linked Proposal: {f.proposal_id})")
    else:
        print(f"FAILURE: Expected 2 entries, found {funnels.count()}.")

    # Update Proposal 1
    print("\nUpdating Proposal 1...")
    proposal1.subject = "Proposal 1 Updated"
    proposal1.save()
    # Assume calculate_totals called if items changed, but here just subject.
    update_sales_funnel(proposal1)
    
    f1 = SalesFunnel.objects.get(proposal=proposal1)
    print(f"Funnel Entry 1 Description: {f1.requirement_description}")
    if f1.requirement_description == "Proposal 1 Updated":
        print("SUCCESS: Funnel Entry 1 updated.")
    else:
        print("FAILURE: Funnel Entry 1 not updated.")

if __name__ == '__main__':
    run_test()
