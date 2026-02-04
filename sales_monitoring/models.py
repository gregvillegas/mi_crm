from django.db import models
from django.utils import timezone
from users.models import User
from customers.models import Customer
from teams.models import Group
import json

class ActivityType(models.Model):
    """Predefined types of sales activities"""
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-circle', help_text='FontAwesome icon class')
    color = models.CharField(max_length=20, default='primary', help_text='Bootstrap color class')
    is_active = models.BooleanField(default=True)
    requires_customer = models.BooleanField(default=True, help_text='Whether this activity type requires a customer association')
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.name

class SalesActivity(models.Model):
    """Individual sales activities performed by salespeople"""
    
    STATUS_CHOICES = [
        ('planned', 'Planned'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('postponed', 'Postponed'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic Information
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    activity_type = models.ForeignKey(ActivityType, on_delete=models.CASCADE, related_name='activities')
    
    # People involved
    salesperson = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_activities',
                                  limit_choices_to={'role': 'salesperson'})
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='activities',
                               null=True, blank=True)
    
    # Activity details
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planned')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium')
    
    # Timing
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_end = models.DateTimeField(null=True, blank=True)
    actual_start = models.DateTimeField(null=True, blank=True)
    actual_end = models.DateTimeField(null=True, blank=True)
    
    # Additional fields for specific activity types
    notes = models.TextField(blank=True, help_text='Notes and outcomes from the activity')
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For supervisor oversight
    reviewed_by_supervisor = models.BooleanField(default=False)
    supervisor_notes = models.TextField(blank=True)
    supervisor_reviewed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-scheduled_start', '-created_at']
        indexes = [
            models.Index(fields=['salesperson', '-scheduled_start']),
            models.Index(fields=['customer', '-scheduled_start']),
            models.Index(fields=['status', '-scheduled_start']),
            models.Index(fields=['activity_type', '-scheduled_start']),
            models.Index(fields=['reviewed_by_supervisor']),
        ]
        verbose_name = 'Sales Activity'
        verbose_name_plural = 'Sales Activities'
    
    def __str__(self):
        return f"{self.title} - {self.salesperson.username} ({self.get_status_display()})"
    
    @property
    def duration_minutes(self):
        """Calculate actual duration in minutes"""
        if self.actual_start and self.actual_end:
            delta = self.actual_end - self.actual_start
            return round(delta.total_seconds() / 60)
        return None
    
    @property
    def is_overdue(self):
        """Check if activity is overdue"""
        if self.scheduled_end and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.scheduled_end
        return False
    
    def mark_reviewed_by_supervisor(self, supervisor_user, notes=''):
        """Mark activity as reviewed by supervisor"""
        self.reviewed_by_supervisor = True
        self.supervisor_notes = notes
        self.supervisor_reviewed_at = timezone.now()
        self.save(update_fields=['reviewed_by_supervisor', 'supervisor_notes', 'supervisor_reviewed_at'])

class CallActivity(models.Model):
    """Specific details for phone calls"""
    sales_activity = models.OneToOneField(SalesActivity, on_delete=models.CASCADE, related_name='call_details')
    phone_number = models.CharField(max_length=20)
    call_type = models.CharField(max_length=20, choices=[
        ('cold', 'Cold Call'),
        ('warm', 'Warm Call'),
        ('follow_up', 'Follow-up Call'),
        ('demo', 'Product Demo'),
        ('support', 'Customer Support'),
    ], default='cold')
    call_outcome = models.CharField(max_length=30, choices=[
        ('answered', 'Call Answered'),
        ('voicemail', 'Left Voicemail'),
        ('busy', 'Busy/No Answer'),
        ('wrong_number', 'Wrong Number'),
        ('not_interested', 'Not Interested'),
        ('interested', 'Interested'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('proposal_requested', 'Proposal Requested'),
    ], blank=True)
    
    def __str__(self):
        return f"Call to {self.phone_number} - {self.get_call_type_display()}"

class MeetingActivity(models.Model):
    """Specific details for meetings"""
    sales_activity = models.OneToOneField(SalesActivity, on_delete=models.CASCADE, related_name='meeting_details')
    meeting_type = models.CharField(max_length=20, choices=[
        ('initial', 'Initial Meeting'),
        ('demo', 'Product Demo'),
        ('proposal', 'Proposal Presentation'),
        ('negotiation', 'Negotiation'),
        ('closing', 'Closing Meeting'),
        ('follow_up', 'Follow-up Meeting'),
    ], default='initial')
    location = models.CharField(max_length=200, blank=True)
    attendees = models.TextField(blank=True, help_text='List of attendees')
    meeting_outcome = models.CharField(max_length=30, choices=[
        ('successful', 'Successful'),
        ('needs_follow_up', 'Needs Follow-up'),
        ('not_interested', 'Not Interested'),
        ('proposal_requested', 'Proposal Requested'),
        ('deal_closed', 'Deal Closed'),
        ('cancelled', 'Cancelled'),
    ], blank=True)
    
    def __str__(self):
        return f"{self.get_meeting_type_display()} at {self.location or 'TBD'}"

class EmailActivity(models.Model):
    """Specific details for email communications"""
    sales_activity = models.OneToOneField(SalesActivity, on_delete=models.CASCADE, related_name='email_details')
    email_type = models.CharField(max_length=20, choices=[
        ('introduction', 'Introduction'),
        ('follow_up', 'Follow-up'),
        ('proposal', 'Proposal'),
        ('quote', 'Quote'),
        ('contract', 'Contract'),
        ('thank_you', 'Thank You'),
        ('newsletter', 'Newsletter'),
    ], default='introduction')
    subject = models.CharField(max_length=200)
    recipients = models.TextField(help_text='Email addresses of recipients')
    has_attachments = models.BooleanField(default=False)
    email_opened = models.BooleanField(default=False, help_text='Whether recipient opened the email')
    email_responded = models.BooleanField(default=False, help_text='Whether recipient responded')
    
    def __str__(self):
        return f"Email: {self.subject}"

class ProposalActivity(models.Model):
    """Specific details for proposals"""
    sales_activity = models.OneToOneField(SalesActivity, on_delete=models.CASCADE, related_name='proposal_details')
    proposal_title = models.CharField(max_length=200)
    proposal_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='PHP')
    proposal_status = models.CharField(max_length=20, choices=[
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('under_review', 'Under Review'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('negotiating', 'Negotiating'),
    ], default='draft')
    expected_decision_date = models.DateField(null=True, blank=True)
    win_probability = models.PositiveIntegerField(default=50, help_text='Probability of winning (0-100%)')
    
    def __str__(self):
        return f"Proposal: {self.proposal_title}"

class TaskActivity(models.Model):
    """Specific details for tasks"""
    sales_activity = models.OneToOneField(SalesActivity, on_delete=models.CASCADE, related_name='task_details')
    task_category = models.CharField(max_length=30, choices=[
        ('research', 'Customer Research'),
        ('preparation', 'Meeting Preparation'),
        ('documentation', 'Documentation'),
        ('follow_up', 'Follow-up Action'),
        ('administrative', 'Administrative'),
        ('training', 'Training/Learning'),
    ], default='administrative')
    estimated_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    actual_hours = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    
    def __str__(self):
        return f"Task: {self.sales_activity.title}"

class ActivityLog(models.Model):
    """Log of all changes to sales activities for audit trail"""
    
    ACTION_CHOICES = [
        ('created', 'Activity Created'),
        ('updated', 'Activity Updated'),
        ('status_changed', 'Status Changed'),
        ('reviewed', 'Reviewed by Supervisor'),
        ('completed', 'Activity Completed'),
        ('cancelled', 'Activity Cancelled'),
    ]
    
    activity = models.ForeignKey(SalesActivity, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    description = models.TextField()
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='activity_logs')
    
    # Store previous and new values for tracking changes
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['activity', '-timestamp']),
            models.Index(fields=['changed_by', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.activity.title} - {self.get_action_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
    
    @classmethod
    def log_activity_change(cls, activity, action, description, changed_by=None, old_value=None, new_value=None):
        """Convenience method to log an activity change"""
        return cls.objects.create(
            activity=activity,
            action=action,
            description=description,
            changed_by=changed_by,
            old_value=old_value,
            new_value=new_value
        )

class SupervisorReport(models.Model):
    """Supervisor reports on team performance"""
    
    REPORT_TYPE_CHOICES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Period Report'),
    ]
    
    supervisor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='supervisor_reports',
                                 limit_choices_to={'role__in': ['supervisor', 'asm']})
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='reports')
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    
    # Report metrics
    total_activities = models.PositiveIntegerField(default=0)
    completed_activities = models.PositiveIntegerField(default=0)
    calls_made = models.PositiveIntegerField(default=0)
    meetings_held = models.PositiveIntegerField(default=0)
    emails_sent = models.PositiveIntegerField(default=0)
    proposals_sent = models.PositiveIntegerField(default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    
    # Performance metrics
    average_activity_completion_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    team_productivity_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['supervisor', '-created_at']),
            models.Index(fields=['group', '-created_at']),
            models.Index(fields=['period_start', 'period_end']),
        ]
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.group.name} ({self.period_start.strftime('%Y-%m-%d')})"
    
    def generate_report_data(self):
        """Generate comprehensive report data"""
        # Get all salespeople in the group
        salespeople = User.objects.filter(
            team_membership__group=self.group,
            role='salesperson',
            is_active=True
        )
        
        report_data = {
            'period': {
                'start': self.period_start,
                'end': self.period_end,
            },
            'salespeople': [],
            'summary': {
                'total_salespeople': salespeople.count(),
                'total_activities': 0,
                'completed_activities': 0,
                'completion_rate': 0,
            }
        }
        
        total_activities = 0
        total_completed = 0
        
        for salesperson in salespeople:
            activities = SalesActivity.objects.filter(
                salesperson=salesperson,
                created_at__gte=self.period_start,
                created_at__lte=self.period_end
            )
            
            completed_activities = activities.filter(status='completed')
            
            salesperson_data = {
                'user': salesperson,
                'total_activities': activities.count(),
                'completed_activities': completed_activities.count(),
                'completion_rate': (completed_activities.count() / activities.count() * 100) if activities.count() > 0 else 0,
                'activities_by_type': {},
            }
            
            # Break down by activity type
            for activity_type in ActivityType.objects.filter(is_active=True):
                type_activities = activities.filter(activity_type=activity_type)
                type_completed = type_activities.filter(status='completed')
                
                salesperson_data['activities_by_type'][activity_type.name] = {
                    'total': type_activities.count(),
                    'completed': type_completed.count(),
                }
            
            report_data['salespeople'].append(salesperson_data)
            total_activities += activities.count()
            total_completed += completed_activities.count()
        
        # Update summary
        report_data['summary']['total_activities'] = total_activities
        report_data['summary']['completed_activities'] = total_completed
        report_data['summary']['completion_rate'] = (total_completed / total_activities * 100) if total_activities > 0 else 0
        
        return report_data

class ActivityReminder(models.Model):
    """Reminders for upcoming or overdue activities"""
    
    REMINDER_TYPE_CHOICES = [
        ('upcoming', 'Upcoming Activity'),
        ('overdue', 'Overdue Activity'),
        ('follow_up', 'Follow-up Required'),
        ('review_needed', 'Supervisor Review Needed'),
    ]
    
    activity = models.ForeignKey(SalesActivity, on_delete=models.CASCADE, related_name='reminders')
    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE_CHOICES)
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activity_reminders')
    message = models.TextField()
    
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read']),
            models.Index(fields=['reminder_type', 'is_sent']),
        ]
    
    def __str__(self):
        return f"{self.get_reminder_type_display()} for {self.activity.title}"
    
    def mark_as_read(self):
        """Mark reminder as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at'])
