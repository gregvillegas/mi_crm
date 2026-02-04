from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from users.models import User
from customers.models import Customer
from sales_funnel.models import SalesFunnel
import json

# Import all models from scoring_models to ensure Django recognizes them
from .scoring_models import *

class LeadSource(models.Model):
    """Sources where leads come from"""
    
    SOURCE_TYPES = [
        ('website', 'Website'),
        ('social_media', 'Social Media'),
        ('referral', 'Referral'),
        ('cold_calling', 'Cold Calling'),
        ('email_marketing', 'Email Marketing'),
        ('advertising', 'Advertising'),
        ('trade_show', 'Trade Show'),
        ('webinar', 'Webinar'),
        ('content_marketing', 'Content Marketing'),
        ('seo', 'SEO/Organic Search'),
        ('paid_search', 'Paid Search'),
        ('partner', 'Partner'),
        ('other', 'Other'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPES)
    description = models.TextField(blank=True)
    cost_per_lead = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Average cost to acquire a lead from this source"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['source_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"
    
    @property
    def total_leads(self):
        """Get total number of leads from this source"""
        return self.leads.count()
    
    @property
    def converted_leads(self):
        """Get number of leads that converted to customers"""
        return self.leads.filter(status='converted').count()
    
    @property
    def conversion_rate(self):
        """Calculate conversion rate percentage"""
        total = self.total_leads
        if total > 0:
            return (self.converted_leads / total) * 100
        return 0
    
    @property
    def total_cost(self):
        """Calculate total cost for all leads from this source"""
        return self.cost_per_lead * self.total_leads


class Lead(models.Model):
    """Individual leads with complete information and tracking"""
    
    STATUS_CHOICES = [
        ('new', 'New Lead'),
        ('contacted', 'Contacted'),
        ('qualified', 'Qualified'),
        ('proposal_sent', 'Proposal Sent'),
        ('negotiating', 'Negotiating'),
        ('converted', 'Converted to Customer'),
        ('lost', 'Lost'),
        ('unqualified', 'Unqualified'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('hot', 'Hot Lead'),
    ]
    
    # Basic Information
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    
    # Location Information
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    territory = models.CharField(
        max_length=50, 
        choices=Customer.TERRITORY_CHOICES, 
        blank=True,
        help_text="Geographic territory/area"
    )
    
    # Business Information
    industry = models.CharField(
        max_length=50, 
        choices=Customer.INDUSTRY_CHOICES, 
        blank=True,
        help_text="Lead's industry sector"
    )
    company_size = models.CharField(
        max_length=20,
        choices=[
            ('1-10', '1-10 employees'),
            ('11-50', '11-50 employees'),
            ('51-200', '51-200 employees'),
            ('201-500', '201-500 employees'),
            ('501-1000', '501-1000 employees'),
            ('1000+', '1000+ employees'),
        ],
        blank=True
    )
    annual_revenue = models.CharField(
        max_length=20,
        choices=[
            ('under_1m', 'Under ₱1M'),
            ('1m_5m', '₱1M - ₱5M'),
            ('5m_10m', '₱5M - ₱10M'),
            ('10m_50m', '₱10M - ₱50M'),
            ('50m_100m', '₱50M - ₱100M'),
            ('over_100m', 'Over ₱100M'),
        ],
        blank=True
    )
    
    # Lead Management
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    source = models.ForeignKey(LeadSource, on_delete=models.CASCADE, related_name='leads')
    assigned_to = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='assigned_leads',
        limit_choices_to={'role': 'salesperson'}
    )
    
    # Interest and Requirements
    initial_interest = models.TextField(blank=True, help_text="What initially interested them?")
    requirements = models.TextField(blank=True, help_text="Specific requirements or needs")
    budget_range = models.CharField(
        max_length=20,
        choices=[
            ('under_10k', 'Under ₱10,000'),
            ('10k_50k', '₱10,000 - ₱50,000'),
            ('50k_100k', '₱50,000 - ₱100,000'),
            ('100k_500k', '₱100,000 - ₱500,000'),
            ('500k_1m', '₱500,000 - ₱1,000,000'),
            ('over_1m', 'Over ₱1,000,000'),
        ],
        blank=True
    )
    timeline = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Immediate (< 1 month)'),
            ('short_term', 'Short term (1-3 months)'),
            ('medium_term', 'Medium term (3-6 months)'),
            ('long_term', 'Long term (6+ months)'),
            ('no_timeline', 'No specific timeline'),
        ],
        blank=True
    )
    
    # Scoring and Quality
    lead_score = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Automated lead score (0-100)"
    )
    
    # Conversion Information
    converted_to_customer = models.ForeignKey(
        Customer,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='original_lead'
    )
    conversion_date = models.DateTimeField(null=True, blank=True)
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Value of the deal when converted"
    )
    
    # Timing
    first_contact_date = models.DateTimeField(null=True, blank=True)
    last_contact_date = models.DateTimeField(null=True, blank=True)
    next_follow_up_date = models.DateTimeField(null=True, blank=True)
    expected_close_date = models.DateTimeField(null=True, blank=True)
    
    # Additional Information
    notes = models.TextField(blank=True)
    is_qualified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'assigned_to']),
            models.Index(fields=['lead_score', '-created_at']),
            models.Index(fields=['source', 'status']),
            models.Index(fields=['priority', '-created_at']),
            models.Index(fields=['next_follow_up_date']),
        ]
    
    def __str__(self):
        company = f" ({self.company_name})" if self.company_name else ""
        return f"{self.first_name} {self.last_name}{company} - {self.get_status_display()}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        """Method version of full_name for compatibility"""
        return self.full_name
    
    @property
    def score(self):
        """Convenience property for lead_score"""
        return self.lead_score
    
    @property
    def qualification_level(self):
        """Return qualification level based on status and score"""
        if self.is_qualified or self.status == 'qualified':
            return 'qualified'
        elif self.lead_score >= 60:
            return 'ready'
        elif self.lead_score >= 30:
            return 'promising'
        else:
            return 'unqualified'
    
    @property
    def days_as_lead(self):
        """Calculate how many days this has been a lead"""
        return (timezone.now() - self.created_at).days
    
    @property
    def is_hot_lead(self):
        """Check if this is a hot lead based on score and priority"""
        return self.priority == 'hot' or self.lead_score >= 80
    
    @property
    def status_color(self):
        """Return Bootstrap color class for status"""
        colors = {
            'new': 'primary',
            'contacted': 'info',
            'qualified': 'success',
            'proposal_sent': 'warning',
            'negotiating': 'warning',
            'converted': 'success',
            'lost': 'danger',
            'unqualified': 'secondary',
        }
        return colors.get(self.status, 'secondary')
    
    @property
    def priority_color(self):
        """Return Bootstrap color class for priority"""
        colors = {
            'low': 'secondary',
            'medium': 'primary',
            'high': 'warning',
            'hot': 'danger',
        }
        return colors.get(self.priority, 'secondary')
    
    def calculate_lead_score(self):
        """Calculate and update lead score based on various factors"""
        score = 0
        
        # Demographic scoring
        if self.company_size:
            size_scores = {
                '1-10': 10, '11-50': 20, '51-200': 30,
                '201-500': 40, '501-1000': 45, '1000+': 50
            }
            score += size_scores.get(self.company_size, 0)
        
        if self.annual_revenue:
            revenue_scores = {
                'under_1m': 5, '1m_5m': 15, '5m_10m': 25,
                '10m_50m': 35, '50m_100m': 45, 'over_100m': 50
            }
            score += revenue_scores.get(self.annual_revenue, 0)
        
        # Budget and timeline scoring
        if self.budget_range:
            budget_scores = {
                'under_10k': 5, '10k_50k': 15, '50k_100k': 25,
                '100k_500k': 35, '500k_1m': 45, 'over_1m': 50
            }
            score += budget_scores.get(self.budget_range, 0)
        
        if self.timeline:
            timeline_scores = {
                'immediate': 25, 'short_term': 20, 'medium_term': 15,
                'long_term': 10, 'no_timeline': 5
            }
            score += timeline_scores.get(self.timeline, 0)
        
        # Engagement scoring based on activities
        activities_count = self.activities.count()
        if activities_count >= 5:
            score += 15
        elif activities_count >= 3:
            score += 10
        elif activities_count >= 1:
            score += 5
        
        # Recent activity bonus
        recent_activity = self.activities.filter(
            created_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).exists()
        if recent_activity:
            score += 10
        
        # Contact information completeness
        completeness = 0
        if self.phone_number:
            completeness += 1
        if self.company_name:
            completeness += 1
        if self.job_title:
            completeness += 1
        if self.industry:
            completeness += 1
        
        score += completeness * 2
        
        # Ensure score is within bounds
        self.lead_score = min(max(score, 0), 100)
        self.save(update_fields=['lead_score'])
        
        return self.lead_score
    
    def convert_to_customer(self, salesperson=None):
        """Convert this lead to a customer"""
        if self.converted_to_customer:
            return self.converted_to_customer
        
        # Create customer from lead data
        customer = Customer.objects.create(
            company_name=self.company_name or f"{self.full_name} Company",
            contact_person_name=self.full_name,
            email=self.email,
            phone_number=self.phone_number,
            address=self.address,
            industry=self.industry,
            territory=self.territory,
            salesperson=salesperson or self.assigned_to,
        )
        
        # Update lead status
        self.status = 'converted'
        self.converted_to_customer = customer
        self.conversion_date = timezone.now()
        self.save(update_fields=['status', 'converted_to_customer', 'conversion_date'])
        
        # Log the conversion
        ConversionTracking.objects.create(
            lead=self,
            customer=customer,
            converted_by=salesperson or self.assigned_to,
            conversion_value=self.conversion_value,
        )
        
        return customer


class LeadActivity(models.Model):
    """Track all activities performed on leads"""
    
    ACTIVITY_TYPES = [
        ('call', 'Phone Call'),
        ('email', 'Email'),
        ('meeting', 'Meeting'),
        ('demo', 'Product Demo'),
        ('proposal', 'Proposal Sent'),
        ('follow_up', 'Follow-up'),
        ('research', 'Research'),
        ('note', 'Note Added'),
        ('status_change', 'Status Changed'),
    ]
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    
    performed_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='lead_activities'
    )
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='created_activities'
    )
    
    # Activity outcome
    outcome = models.CharField(
        max_length=30,
        choices=[
            ('successful', 'Successful'),
            ('no_response', 'No Response'),
            ('interested', 'Showed Interest'),
            ('not_interested', 'Not Interested'),
            ('follow_up_needed', 'Follow-up Needed'),
            ('meeting_scheduled', 'Meeting Scheduled'),
            ('proposal_requested', 'Proposal Requested'),
        ],
        blank=True
    )
    
    # Follow-up information
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    activity_date = models.DateTimeField(default=timezone.now)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['performed_by', '-created_at']),
        ]
        verbose_name = 'Lead Activity'
        verbose_name_plural = 'Lead Activities'
    
    def __str__(self):
        return f"{self.lead.full_name} - {self.get_activity_type_display()}: {self.title}"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update lead's last contact date
        self.lead.last_contact_date = self.created_at
        if not self.lead.first_contact_date:
            self.lead.first_contact_date = self.created_at
        self.lead.save(update_fields=['last_contact_date', 'first_contact_date'])
        
        # Recalculate lead score
        self.lead.calculate_lead_score()


class LeadScoring(models.Model):
    """Store detailed scoring breakdown for leads"""
    
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='scoring_details')
    
    # Individual score components
    demographic_score = models.IntegerField(default=0)
    company_score = models.IntegerField(default=0)
    behavioral_score = models.IntegerField(default=0)
    engagement_score = models.IntegerField(default=0)
    fit_score = models.IntegerField(default=0)
    
    # Scoring factors breakdown (JSON field)
    scoring_breakdown = models.JSONField(default=dict, blank=True)
    
    last_calculated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Lead Scoring Detail'
        verbose_name_plural = 'Lead Scoring Details'
    
    def __str__(self):
        return f"Scoring for {self.lead.full_name} - Total: {self.total_score}"
    
    @property
    def total_score(self):
        return (
            self.demographic_score + self.company_score + 
            self.behavioral_score + self.engagement_score + self.fit_score
        )


class ConversionTracking(models.Model):
    """Track lead to customer conversions"""
    
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='conversions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='conversion_history')
    
    converted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='conversions_made'
    )
    
    # Conversion details
    conversion_date = models.DateTimeField(auto_now_add=True)
    days_to_convert = models.IntegerField(help_text="Days from lead creation to conversion")
    conversion_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Initial deal value when converted"
    )
    
    # Lead source cost tracking
    acquisition_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Cost to acquire this lead"
    )
    
    # Associated sales funnel entry
    sales_funnel_entry = models.ForeignKey(
        SalesFunnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='conversion_source'
    )
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-conversion_date']
        indexes = [
            models.Index(fields=['conversion_date']),
            models.Index(fields=['converted_by', '-conversion_date']),
        ]
    
    def __str__(self):
        return f"{self.lead.full_name} -> {self.customer.company_name}"
    
    @property
    def roi(self):
        """Calculate ROI if conversion value and acquisition cost are available"""
        if self.conversion_value and self.acquisition_cost > 0:
            return ((self.conversion_value - self.acquisition_cost) / self.acquisition_cost) * 100
        return None
    
    def save(self, *args, **kwargs):
        if not self.days_to_convert:
            self.days_to_convert = (
                self.conversion_date.date() - self.lead.created_at.date()
            ).days
        
        if not self.acquisition_cost and self.lead.source:
            self.acquisition_cost = self.lead.source.cost_per_lead
        
        super().save(*args, **kwargs)


class LeadNurturingCampaign(models.Model):
    """Automated campaigns for nurturing leads"""
    
    name = models.CharField(max_length=200)
    description = models.TextField()
    
    # Campaign targeting
    target_status = models.CharField(
        max_length=20, 
        choices=Lead.STATUS_CHOICES,
        help_text="Target leads with this status"
    )
    target_score_min = models.IntegerField(
        default=0,
        help_text="Minimum lead score to target"
    )
    target_score_max = models.IntegerField(
        default=100,
        help_text="Maximum lead score to target"
    )
    
    # Campaign content
    email_template = models.TextField(blank=True)
    follow_up_days = models.IntegerField(
        default=7,
        help_text="Days after which to follow up"
    )
    
    # Campaign settings
    is_active = models.BooleanField(default=True)
    auto_assign_salesperson = models.BooleanField(
        default=False,
        help_text="Automatically assign leads to salespeople"
    )
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def get_eligible_leads(self):
        """Get leads that are eligible for this campaign"""
        return Lead.objects.filter(
            status=self.target_status,
            lead_score__gte=self.target_score_min,
            lead_score__lte=self.target_score_max,
            is_active=True
        )
