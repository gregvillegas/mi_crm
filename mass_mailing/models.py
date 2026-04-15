import uuid
from django.db import models
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
    TEMPLATE_CHOICES = (
        ('html', 'Custom HTML'),
        ('hero_promo', 'Hero Promo'),
        ('product_launch', 'Product Launch'),
        ('product_of_week', 'Product Of The Week'),
        ('newsletter_digest', 'Newsletter Digest'),
    )
    
    name = models.CharField(max_length=200, help_text="Internal name for this campaign")
    subject = models.CharField(max_length=255, help_text="Email subject line")
    body_html = models.TextField(help_text="HTML body of the email. Available variables: {{ contact_name }}, {{ company_name }}")
    template_type = models.CharField(max_length=30, choices=TEMPLATE_CHOICES, default='html')
    hero_headline = models.CharField(max_length=255, blank=True)
    hero_intro = models.TextField(blank=True)
    hero_bullet_1 = models.CharField(max_length=255, blank=True)
    hero_bullet_2 = models.CharField(max_length=255, blank=True)
    hero_bullet_3 = models.CharField(max_length=255, blank=True)
    hero_cta_label = models.CharField(max_length=100, blank=True)
    hero_cta_url = models.URLField(blank=True)
    
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='campaigns')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    RECIPIENT_MODE_CHOICES = (
        ('crm', 'CRM Customers'),
        ('csv', 'CSV Upload'),
        ('manual', 'Manual Entry'),
    )
    recipient_mode = models.CharField(max_length=20, choices=RECIPIENT_MODE_CHOICES, default='crm')
    
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

    def inline_assets(self):
        return self.assets.filter(embed_inline=True).order_by('sort_order', 'uploaded_at')

    def attachment_assets(self):
        return self.assets.filter(embed_inline=False).order_by('sort_order', 'uploaded_at')


class MediaLibraryAsset(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='campaign_library/')
    is_active = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_media_library_assets')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Media Library Asset'
        verbose_name_plural = 'Media Library Assets'

    def __str__(self):
        return self.title

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
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, null=True, blank=True)
    source_type = models.CharField(max_length=20, default='customer')
    company_name = models.CharField(max_length=255, blank=True)
    contact_name = models.CharField(max_length=255, blank=True)
    position = models.CharField(max_length=255, blank=True)
    email = models.EmailField() # Stored separately in case customer email changes later
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.email} - {self.campaign.name}"

    @property
    def display_company_name(self):
        if self.company_name:
            return self.company_name
        if self.customer_id:
            return self.customer.company_name
        return ''

    @property
    def display_contact_name(self):
        if self.contact_name:
            return self.contact_name
        if self.customer_id:
            return self.customer.contact_person_name
        return ''


class CampaignAsset(models.Model):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='assets')
    library_asset = models.ForeignKey(MediaLibraryAsset, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaign_assets')
    file = models.FileField(upload_to='campaign_assets/')
    display_name = models.CharField(max_length=255, blank=True)
    embed_inline = models.BooleanField(default=True, help_text="Embed this image inline in the email body")
    sort_order = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_campaign_assets')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'uploaded_at']

    def __str__(self):
        return self.display_name or self.file.name.rsplit('/', 1)[-1]
