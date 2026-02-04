from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
import json

class ScoringCriteria(models.Model):
    """Configurable scoring criteria for leads"""
    
    CRITERIA_TYPES = [
        ('demographic', 'Demographic'),
        ('firmographic', 'Firmographic'),
        ('behavioral', 'Behavioral'),
        ('engagement', 'Engagement'),
        ('source', 'Source Quality'),
        ('temporal', 'Temporal'),
    ]
    
    name = models.CharField(max_length=100)
    criteria_type = models.CharField(max_length=20, choices=CRITERIA_TYPES)
    description = models.TextField()
    weight = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.00,
        help_text="Weight multiplier for this criteria (0.1 to 10.0)"
    )
    max_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text="Maximum points this criteria can contribute"
    )
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['criteria_type', 'name']
        verbose_name_plural = 'Scoring Criteria'
    
    def __str__(self):
        return f"{self.name} ({self.get_criteria_type_display()}) - Weight: {self.weight}"


class ScoringRule(models.Model):
    """Individual scoring rules with conditions and points"""
    
    COMPARISON_OPERATORS = [
        ('eq', 'Equals'),
        ('gt', 'Greater than'),
        ('gte', 'Greater than or equal'),
        ('lt', 'Less than'),
        ('lte', 'Less than or equal'),
        ('contains', 'Contains'),
        ('in', 'In list'),
        ('not_in', 'Not in list'),
        ('is_null', 'Is empty/null'),
        ('is_not_null', 'Is not empty/null'),
        ('regex', 'Matches pattern'),
    ]
    
    criteria = models.ForeignKey(ScoringCriteria, on_delete=models.CASCADE, related_name='rules')
    
    # Rule definition
    field_name = models.CharField(
        max_length=100, 
        help_text="Lead model field name (e.g., 'company_size', 'annual_revenue')"
    )
    operator = models.CharField(max_length=20, choices=COMPARISON_OPERATORS)
    value = models.TextField(help_text="Value to compare against (JSON for complex values)")
    
    # Scoring
    points = models.IntegerField(
        validators=[MinValueValidator(-100), MaxValueValidator(100)],
        help_text="Points awarded when this rule matches (-100 to 100)"
    )
    
    # Metadata
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0, help_text="Evaluation order")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['criteria', 'order', 'id']
    
    def __str__(self):
        return f"{self.criteria.name}: {self.field_name} {self.operator} {self.value} = {self.points}pts"
    
    def evaluate_lead(self, lead):
        """Evaluate this rule against a lead and return points"""
        try:
            # Get the field value from the lead
            field_value = getattr(lead, self.field_name, None)
            
            # Parse the comparison value
            try:
                comparison_value = json.loads(self.value)
            except (json.JSONDecodeError, TypeError):
                comparison_value = self.value
            
            # Perform the comparison
            if self.operator == 'eq':
                matches = field_value == comparison_value
            elif self.operator == 'gt':
                matches = field_value is not None and field_value > comparison_value
            elif self.operator == 'gte':
                matches = field_value is not None and field_value >= comparison_value
            elif self.operator == 'lt':
                matches = field_value is not None and field_value < comparison_value
            elif self.operator == 'lte':
                matches = field_value is not None and field_value <= comparison_value
            elif self.operator == 'contains':
                matches = field_value is not None and comparison_value in str(field_value)
            elif self.operator == 'in':
                matches = field_value in comparison_value if isinstance(comparison_value, list) else False
            elif self.operator == 'not_in':
                matches = field_value not in comparison_value if isinstance(comparison_value, list) else True
            elif self.operator == 'is_null':
                matches = field_value is None or field_value == ''
            elif self.operator == 'is_not_null':
                matches = field_value is not None and field_value != ''
            elif self.operator == 'regex':
                import re
                matches = bool(re.match(comparison_value, str(field_value or '')))
            else:
                matches = False
            
            return self.points if matches else 0
            
        except Exception as e:
            # Log error in production
            print(f"Scoring rule evaluation error: {e}")
            return 0


class LeadScoringProfile(models.Model):
    """Scoring profile that groups criteria for different lead types"""
    
    name = models.CharField(max_length=100)
    description = models.TextField()
    criteria = models.ManyToManyField(ScoringCriteria, through='ProfileCriteria')
    
    # Profile settings
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # Auto-assignment rules
    auto_assign_threshold = models.IntegerField(
        default=80,
        help_text="Score threshold for automatic assignment to salespeople"
    )
    hot_lead_threshold = models.IntegerField(
        default=75,
        help_text="Score threshold to mark leads as 'hot'"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure only one default profile
        if self.is_default:
            LeadScoringProfile.objects.exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class ProfileCriteria(models.Model):
    """Through model for profile-criteria relationship with custom weights"""
    
    profile = models.ForeignKey(LeadScoringProfile, on_delete=models.CASCADE)
    criteria = models.ForeignKey(ScoringCriteria, on_delete=models.CASCADE)
    weight_multiplier = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.00,
        help_text="Profile-specific weight multiplier"
    )
    is_enabled = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['profile', 'criteria']


class ActivityScoringRule(models.Model):
    """Scoring rules based on lead activities and engagement"""
    
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
    
    OUTCOME_TYPES = [
        ('successful', 'Successful'),
        ('no_response', 'No Response'),
        ('interested', 'Showed Interest'),
        ('not_interested', 'Not Interested'),
        ('follow_up_needed', 'Follow-up Needed'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('proposal_requested', 'Proposal Requested'),
    ]
    
    name = models.CharField(max_length=100)
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES, blank=True)
    outcome = models.CharField(max_length=30, choices=OUTCOME_TYPES, blank=True)
    
    # Scoring parameters
    points_per_activity = models.IntegerField(default=5)
    max_points_per_day = models.IntegerField(default=25)
    decay_days = models.IntegerField(
        default=30, 
        help_text="Days after which activity points start decaying"
    )
    decay_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0.10,
        help_text="Daily decay rate (0.10 = 10% per day)"
    )
    
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['activity_type', 'outcome']
    
    def __str__(self):
        activity_desc = f"Activity: {self.get_activity_type_display()}" if self.activity_type else "Any Activity"
        outcome_desc = f", Outcome: {self.get_outcome_display()}" if self.outcome else ""
        return f"{self.name} ({activity_desc}{outcome_desc}) = {self.points_per_activity}pts"


class LeadScoreHistory(models.Model):
    """Historical tracking of lead score changes"""
    
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='score_history')
    
    # Score details
    total_score = models.IntegerField()
    demographic_score = models.IntegerField(default=0)
    firmographic_score = models.IntegerField(default=0)
    behavioral_score = models.IntegerField(default=0)
    engagement_score = models.IntegerField(default=0)
    source_score = models.IntegerField(default=0)
    temporal_score = models.IntegerField(default=0)
    
    # Calculation details
    scoring_profile = models.ForeignKey(LeadScoringProfile, on_delete=models.SET_NULL, null=True)
    calculation_details = models.JSONField(default=dict)
    
    # Change tracking
    score_change = models.IntegerField(default=0)
    change_reason = models.CharField(max_length=200, blank=True)
    triggered_by = models.CharField(max_length=100, blank=True)  # What caused the recalculation
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['lead', '-created_at']),
            models.Index(fields=['total_score']),
        ]
    
    def __str__(self):
        change_indicator = f"({self.score_change:+d})" if self.score_change != 0 else ""
        return f"{self.lead.full_name}: {self.total_score} {change_indicator} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"


class ScoringAlert(models.Model):
    """Alerts triggered by scoring thresholds"""
    
    ALERT_TYPES = [
        ('hot_lead', 'Hot Lead Alert'),
        ('score_increase', 'Score Increase Alert'),
        ('score_decrease', 'Score Decrease Alert'),
        ('threshold_reached', 'Threshold Reached'),
        ('assignment_needed', 'Assignment Needed'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    lead = models.ForeignKey('Lead', on_delete=models.CASCADE, related_name='scoring_alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    
    # Alert details
    title = models.CharField(max_length=200)
    message = models.TextField()
    threshold_value = models.IntegerField(null=True, blank=True)
    current_score = models.IntegerField()
    
    # Recipients
    assigned_to = models.ForeignKey(
        'users.User', 
        on_delete=models.CASCADE, 
        related_name='scoring_alerts',
        null=True, 
        blank=True
    )
    notify_supervisors = models.BooleanField(default=False)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='acknowledged_alerts'
    )
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'is_read']),
            models.Index(fields=['alert_type', 'priority']),
        ]
    
    def __str__(self):
        return f"{self.get_alert_type_display()}: {self.lead.full_name} (Score: {self.current_score})"
    
    def acknowledge(self, user):
        """Mark alert as acknowledged"""
        self.is_acknowledged = True
        self.acknowledged_by = user
        self.acknowledged_at = timezone.now()
        self.save(update_fields=['is_acknowledged', 'acknowledged_by', 'acknowledged_at'])
