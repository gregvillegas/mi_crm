import uuid
from django.db import models
from django.utils import timezone
from users.models import User
from customers.models import Customer

class Campaign(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    name = models.CharField(max_length=200, help_text="Internal name for this campaign")
    subject = models.CharField(max_length=255, help_text="Email subject line")
    body_html = models.TextField(help_text="HTML body of the email. Available variables: {{ contact_name }}, {{ company_name }}")
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, help_text="Leave blank to send immediately")
    
    # DPA Compliance Flags
    include_unsubscribe = models.BooleanField(default=True, help_text="Mandatory for DPA compliance")
    
    # Tracking
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)

    def __str__(self):
        return self.name
        
    def update_counts(self):
        self.total_recipients = self.recipients.count()
        self.sent_count = self.recipients.filter(status='sent').count()
        self.failed_count = self.recipients.filter(status='failed').count()
        if self.sent_count + self.failed_count == self.total_recipients and self.total_recipients > 0:
            self.status = 'completed'
        self.save()

class OptOut(models.Model):
    """Tracks users who have unsubscribed (DPA Compliance)"""
    email = models.EmailField(unique=True)
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True)
    opted_out_at = models.DateTimeField(auto_now_add=True)
    reason = models.CharField(max_length=255, blank=True)
    
    def __str__(self):
        return self.email

class CampaignRecipient(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('opted_out', 'Opted Out'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='recipients')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    email = models.EmailField() # Stored separately in case customer email changes later
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.email} - {self.campaign.name}"
