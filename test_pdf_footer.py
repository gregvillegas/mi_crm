
import os
import django
import sys
from reportlab.pdfgen import canvas

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'crm_project.settings')
django.setup()

from sales_proposals.models import Proposal, ProposalItem
from sales_proposals.views import generate_pdf_buffer
from users.models import User
from customers.models import Customer
from django.utils import timezone

def test_pdf_generation():
    print("Setting up test data...")
    user, _ = User.objects.get_or_create(username='pdf_tester', email='pdf@test.com', role='salesperson')
    if not user.check_password('password'):
        user.set_password('password')
        user.save()
        
    customer, _ = Customer.objects.get_or_create(company_name='PDF Test Corp', contact_person_name='PDF Tester', email='pdf@test.com')
    
    proposal = Proposal.objects.create(
        customer=customer,
        created_by=user,
        subject="Footer Test Proposal",
        date=timezone.now().date(),
        status='draft'
    )
    
    # Add enough items to potentially span multiple pages? 
    # Or just test that it generates without error.
    # Let's add 20 items to force a second page.
    for i in range(20):
        ProposalItem.objects.create(
            proposal=proposal,
            description=f"Item {i+1}",
            quantity=1,
            unit_price=1000,
            unit_cost=500
        )
    
    proposal.calculate_totals()
    
    print("Generating PDF...")
    try:
        buffer = generate_pdf_buffer(proposal)
        pdf_content = buffer.getvalue()
        
        output_path = 'test_proposal_footer.pdf'
        with open(output_path, 'wb') as f:
            f.write(pdf_content)
            
        print(f"PDF generated successfully: {output_path} ({len(pdf_content)} bytes)")
        
        # Check if footer image is embedded?
        # It's hard to check binary PDF content for visual elements, but we can check if the file size is reasonable
        # and if the string 'PROPOSAL-FOOTER' is in the source code (it won't be in the PDF binary like that usually).
        
    except Exception as e:
        print(f"FAILED to generate PDF: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_pdf_generation()
