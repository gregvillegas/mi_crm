from django.db import models
from users.models import User
from customers.models import Customer
from django.utils import timezone
from decimal import Decimal

class Proposal(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]

    proposal_number = models.CharField(max_length=50, unique=True, editable=False)
    reference_number = models.CharField(max_length=50, blank=True, null=True, help_text="Optional manual reference number (e.g., Ref No: GGV03022026155)")
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='proposals')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_proposals')
    date = models.DateField(default=timezone.now)
    valid_until = models.DateField(null=True, blank=True)
    subject = models.CharField(max_length=200)
    
    # Currency
    CURRENCY_CHOICES = [
        ('PHP', 'PHP - Philippine Peso'),
        ('USD', 'USD - US Dollar'),
    ]
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='PHP')
    exchange_rate = models.DecimalField(max_digits=10, decimal_places=2, default=1.00, help_text="Exchange rate to PHP (1.0 for PHP)")

    # Terms
    payment_terms = models.CharField(max_length=200, default="30 days", help_text="e.g., 30 days, Cash on Delivery")
    delivery_lead_time = models.CharField(max_length=200, default="Within five (5) to ten (10) working days from receipt of confirmed purchased order.", help_text="e.g., 5-10 working days")
    warranty = models.CharField(max_length=200, default="1 year - Parts Warranty", help_text="e.g., 1 year - Parts Warranty")
    
    CANCELLATION_CHOICES = [
        ('professional', 'Professional and Direct'),
        ('process', 'Process-Oriented'),
        ('polite', 'Short and Polite'),
        ('partnership', 'Partnership-focused'),
    ]
    cancellation_terms = models.CharField(max_length=20, choices=CANCELLATION_CHOICES, default='professional', help_text="Select the tone/wording for the cancellation policy")
    
    # Content
    special_note = models.TextField(help_text="Optional special note (e.g. SUBJECT PRICE CHANGE...)", blank=True)
    introduction = models.TextField(help_text="Opening text of the proposal", blank=True)
    closing = models.TextField(help_text="Terms and conditions or closing text", blank=True)
    
    # Optional Fields
    include_bank_details = models.BooleanField(default=False, help_text="Include bank details in the proposal PDF")
    
    # Financials
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    TAX_TYPE_CHOICES = [
        ('VAT', 'VAT (12%)'),
        ('ZERO', 'Zero-Rated (0%)'),
        ('EXEMPT', 'VAT-Exempt (0%)'),
    ]
    tax_type = models.CharField(max_length=10, choices=TAX_TYPE_CHOICES, default='VAT')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('12.00'), help_text="Tax rate in percentage (e.g. 12 for 12%)")
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Costing (Internal)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total cost of all items")
    gross_profit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total Amount - Total Cost")
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.proposal_number:
            # Generate ID: PROP-YYYY-XXXX
            today = timezone.now()
            # Simple counter, might have race conditions in high concurrency but fine for this scale
            count = Proposal.objects.filter(created_at__year=today.year).count() + 1
            self.proposal_number = f"PROP-{today.year}-{count:04d}"
        # Autogenerate Reference Number: III + MMDDYYYY + ### (per-salesperson sequence)
        if not self.reference_number and self.created_by_id:
            # Initials
            initials = (self.created_by.initials or "").upper()
            if not initials:
                parts = [self.created_by.first_name, self.created_by.last_name]
                initials = "".join((p[:1] or "").upper() for p in parts)[:3].ljust(3, "X")
            elif len(initials) < 3:
                initials = initials.ljust(3, "X")
            # Date string from proposal date
            date_obj = self.date or timezone.now().date()
            date_str = date_obj.strftime("%m%d%Y")
            # Sequence per salesperson
            seq = Proposal.objects.filter(created_by_id=self.created_by_id).count() + 1
            ref = f"{initials}{date_str}{seq:03d}"
            # Ensure uniqueness in rare race conditions
            while Proposal.objects.filter(reference_number=ref).exists():
                seq += 1
                ref = f"{initials}{date_str}{seq:03d}"
            self.reference_number = ref
        super().save(*args, **kwargs)
    
    def calculate_totals(self):
        self.subtotal = sum(item.amount for item in self.items.all())
        self.total_cost = sum(item.total_cost for item in self.items.all())
        
        # Override tax_rate based on tax_type
        if self.tax_type in ['ZERO', 'EXEMPT']:
            self.tax_rate = Decimal('0.00')
        elif self.tax_type == 'VAT' and self.tax_rate == 0:
            self.tax_rate = Decimal('12.00')
            
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount
        
        # Gross profit is Total Revenue (excl tax if we consider net sales, but typically GP is Sales - COGS)
        # Assuming subtotal is Net Sales.
        self.gross_profit = self.subtotal - self.total_cost
        
        self.save()

    def __str__(self):
        return f"{self.proposal_number} - {self.customer.company_name}"

    class Meta:
        ordering = ['-created_at']

class ProposalItem(models.Model):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name='items')
    part_number = models.CharField(max_length=100, blank=True, help_text="Product Part Number")
    description = models.TextField(help_text="Item description and specifications")
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Internal")
    availability = models.CharField(max_length=100, blank=True, help_text="Product availability (e.g. In Stock, 2-3 weeks)")
    amount = models.DecimalField(max_digits=12, decimal_places=2, editable=False)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0, editable=False)

    def save(self, *args, **kwargs):
        self.amount = self.quantity * self.unit_price
        self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)
