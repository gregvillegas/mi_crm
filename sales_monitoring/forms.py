from django import forms
from django.utils import timezone
from django.core.exceptions import ValidationError
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, Button, Div
from .models import (
    SalesActivity, ActivityType, CallActivity, MeetingActivity,
    EmailActivity, ProposalActivity, TaskActivity, ActivityReminder
)
from customers.models import Customer
from users.models import User

class SalesActivityForm(forms.ModelForm):
    class Meta:
        model = SalesActivity
        fields = [
            'title', 'description', 'activity_type', 'customer', 'status', 'priority',
            'scheduled_start', 'scheduled_end', 'notes', 'follow_up_required', 'follow_up_date'
        ]
        widgets = {
            'scheduled_start': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'scheduled_end': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 3}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Limit customers to those assigned to the current user if they're a salesperson
        if self.user and self.user.role == 'salesperson':
            self.fields['customer'].queryset = Customer.objects.filter(
                salesperson=self.user, is_active=True
            )
        
        # Set up crispy forms
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Activity Details',
                Row(
                    Column('title', css_class='form-group col-md-8'),
                    Column('activity_type', css_class='form-group col-md-4'),
                ),
                'description',
                Row(
                    Column('customer', css_class='form-group col-md-6'),
                    Column('priority', css_class='form-group col-md-3'),
                    Column('status', css_class='form-group col-md-3'),
                ),
            ),
            Fieldset(
                'Scheduling',
                Row(
                    Column('scheduled_start', css_class='form-group col-md-6'),
                    Column('scheduled_end', css_class='form-group col-md-6'),
                ),
            ),
            Fieldset(
                'Follow-up',
                Row(
                    Column('follow_up_required', css_class='form-group col-md-4'),
                    Column('follow_up_date', css_class='form-group col-md-8'),
                ),
                'notes',
            ),
            Submit('submit', 'Save Activity', css_class='btn btn-primary'),
            Button('cancel', 'Cancel', css_class='btn btn-secondary', onclick='history.back()'),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        scheduled_start = cleaned_data.get('scheduled_start')
        scheduled_end = cleaned_data.get('scheduled_end')
        follow_up_required = cleaned_data.get('follow_up_required')
        follow_up_date = cleaned_data.get('follow_up_date')
        activity_type = cleaned_data.get('activity_type')
        customer = cleaned_data.get('customer')
        
        # Validate scheduling
        if scheduled_start and scheduled_end:
            if scheduled_end <= scheduled_start:
                raise ValidationError('End time must be after start time.')
        
        # Validate follow-up
        if follow_up_required and not follow_up_date:
            raise ValidationError('Follow-up date is required when follow-up is marked as required.')
        
        # Validate customer requirement
        if activity_type and activity_type.requires_customer and not customer:
            raise ValidationError(f'Customer is required for {activity_type.name} activities.')
        
        return cleaned_data

class CallActivityForm(forms.ModelForm):
    class Meta:
        model = CallActivity
        fields = ['phone_number', 'call_type', 'call_outcome']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('phone_number', css_class='form-group col-md-6'),
                Column('call_type', css_class='form-group col-md-6'),
            ),
            'call_outcome',
        )

class MeetingActivityForm(forms.ModelForm):
    class Meta:
        model = MeetingActivity
        fields = ['meeting_type', 'location', 'attendees', 'meeting_outcome']
        widgets = {
            'attendees': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('meeting_type', css_class='form-group col-md-6'),
                Column('location', css_class='form-group col-md-6'),
            ),
            'attendees',
            'meeting_outcome',
        )

class EmailActivityForm(forms.ModelForm):
    class Meta:
        model = EmailActivity
        fields = ['email_type', 'subject', 'recipients', 'has_attachments', 'email_opened', 'email_responded']
        widgets = {
            'recipients': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('email_type', css_class='form-group col-md-6'),
                Column('subject', css_class='form-group col-md-6'),
            ),
            'recipients',
            Row(
                Column('has_attachments', css_class='form-group col-md-4'),
                Column('email_opened', css_class='form-group col-md-4'),
                Column('email_responded', css_class='form-group col-md-4'),
            ),
        )

class ProposalActivityForm(forms.ModelForm):
    class Meta:
        model = ProposalActivity
        fields = [
            'proposal_title', 'proposal_value', 'currency', 'proposal_status',
            'expected_decision_date', 'win_probability'
        ]
        widgets = {
            'expected_decision_date': forms.DateInput(attrs={'type': 'date'}),
            'win_probability': forms.NumberInput(attrs={'min': 0, 'max': 100, 'step': 5}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'proposal_title',
            Row(
                Column('proposal_value', css_class='form-group col-md-4'),
                Column('currency', css_class='form-group col-md-4'),
                Column('proposal_status', css_class='form-group col-md-4'),
            ),
            Row(
                Column('expected_decision_date', css_class='form-group col-md-6'),
                Column('win_probability', css_class='form-group col-md-6'),
            ),
        )

class TaskActivityForm(forms.ModelForm):
    class Meta:
        model = TaskActivity
        fields = ['task_category', 'estimated_hours', 'actual_hours']
        widgets = {
            'estimated_hours': forms.NumberInput(attrs={'step': 0.5, 'min': 0}),
            'actual_hours': forms.NumberInput(attrs={'step': 0.5, 'min': 0}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'task_category',
            Row(
                Column('estimated_hours', css_class='form-group col-md-6'),
                Column('actual_hours', css_class='form-group col-md-6'),
            ),
        )

class ActivityUpdateForm(forms.ModelForm):
    """Form for updating activity status and completion"""
    actual_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    actual_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    
    class Meta:
        model = SalesActivity
        fields = ['status', 'actual_start', 'actual_end', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'status',
            Row(
                Column('actual_start', css_class='form-group col-md-6'),
                Column('actual_end', css_class='form-group col-md-6'),
            ),
            'notes',
            Submit('submit', 'Update Activity', css_class='btn btn-primary'),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        status = cleaned_data.get('status')
        actual_start = cleaned_data.get('actual_start')
        actual_end = cleaned_data.get('actual_end')
        
        if status == 'completed' and not actual_end:
            raise ValidationError('Actual end time is required when marking activity as completed.')
        
        if actual_start and actual_end and actual_end <= actual_start:
            raise ValidationError('Actual end time must be after actual start time.')
        
        return cleaned_data

class SupervisorReviewForm(forms.Form):
    """Form for supervisors to review and add notes to activities"""
    supervisor_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 4}),
        required=False,
        help_text='Add your review notes here'
    )
    mark_as_reviewed = forms.BooleanField(
        required=False,
        initial=True,
        help_text='Check to mark this activity as reviewed'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            'supervisor_notes',
            'mark_as_reviewed',
            Submit('submit', 'Submit Review', css_class='btn btn-success'),
            Button('cancel', 'Cancel', css_class='btn btn-secondary', onclick='history.back()'),
        )

class ActivityFilterForm(forms.Form):
    """Form for filtering activities in supervisor dashboard"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + SalesActivity.STATUS_CHOICES
    PRIORITY_CHOICES = [('', 'All Priorities')] + SalesActivity.PRIORITY_CHOICES
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='From Date'
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label='To Date'
    )
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False
    )
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False
    )
    activity_type = forms.ModelChoiceField(
        queryset=ActivityType.objects.filter(is_active=True),
        required=False,
        empty_label='All Activity Types'
    )
    salesperson = forms.ModelChoiceField(
        queryset=User.objects.filter(role='salesperson', is_active=True),
        required=False,
        empty_label='All Salespeople'
    )
    reviewed_only = forms.BooleanField(
        required=False,
        label='Show only reviewed activities'
    )
    overdue_only = forms.BooleanField(
        required=False,
        label='Show only overdue activities'
    )
    
    def __init__(self, *args, **kwargs):
        supervisor_user = kwargs.pop('supervisor_user', None)
        super().__init__(*args, **kwargs)
        
        # Limit salesperson choices to those in supervisor's groups
        if supervisor_user and supervisor_user.role == 'supervisor':
            supervised_groups = supervisor_user.managed_groups.all()
            salesperson_ids = []
            for group in supervised_groups:
                salesperson_ids.extend(
                    group.members.filter(user__role='salesperson').values_list('user_id', flat=True)
                )
            self.fields['salesperson'].queryset = User.objects.filter(
                id__in=salesperson_ids,
                is_active=True
            )
        
        self.helper = FormHelper()
        self.helper.form_method = 'GET'
        self.helper.layout = Layout(
            Row(
                Column('date_from', css_class='form-group col-md-3'),
                Column('date_to', css_class='form-group col-md-3'),
                Column('status', css_class='form-group col-md-3'),
                Column('priority', css_class='form-group col-md-3'),
            ),
            Row(
                Column('activity_type', css_class='form-group col-md-4'),
                Column('salesperson', css_class='form-group col-md-4'),
                Column(
                    Div(
                        'reviewed_only',
                        'overdue_only',
                        css_class='mt-2'
                    ),
                    css_class='form-group col-md-4'
                ),
            ),
            Submit('filter', 'Apply Filters', css_class='btn btn-primary'),
            Button('reset', 'Reset', css_class='btn btn-outline-secondary', onclick='window.location.href=window.location.pathname'),
        )

class QuickActivityForm(forms.ModelForm):
    """Simplified form for quick activity logging"""
    
    class Meta:
        model = SalesActivity
        fields = ['title', 'activity_type', 'customer', 'status', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 2}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user and user.role == 'salesperson':
            self.fields['customer'].queryset = Customer.objects.filter(
                salesperson=user, is_active=True
            )
        
        # Auto-set scheduled times to current time for quick entries
        now = timezone.now()
        self.fields['scheduled_start'] = forms.DateTimeField(
            initial=now,
            widget=forms.HiddenInput()
        )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'scheduled_start',  # Hidden field
            'title',
            Row(
                Column('activity_type', css_class='form-group col-md-4'),
                Column('customer', css_class='form-group col-md-4'),
                Column('status', css_class='form-group col-md-4'),
            ),
            'notes',
            Submit('submit', 'Log Activity', css_class='btn btn-success'),
        )

class BulkActivityUpdateForm(forms.Form):
    """Form for bulk updating multiple activities"""
    
    STATUS_CHOICES = [('', 'Keep Current')] + SalesActivity.STATUS_CHOICES
    
    activities = forms.ModelMultipleChoiceField(
        queryset=SalesActivity.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    new_status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        label='Update Status'
    )
    mark_as_reviewed = forms.BooleanField(
        required=False,
        label='Mark as Reviewed by Supervisor'
    )
    supervisor_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        label='Supervisor Notes'
    )
    
    def __init__(self, *args, **kwargs):
        supervisor_user = kwargs.pop('supervisor_user', None)
        super().__init__(*args, **kwargs)
        
        # Limit activities to those from supervisor's team
        if supervisor_user:
            supervised_groups = supervisor_user.managed_groups.all()
            salesperson_ids = []
            for group in supervised_groups:
                salesperson_ids.extend(
                    group.members.filter(user__role='salesperson').values_list('user_id', flat=True)
                )
            
            self.fields['activities'].queryset = SalesActivity.objects.filter(
                salesperson_id__in=salesperson_ids
            ).select_related('salesperson', 'customer', 'activity_type')
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'activities',
            Fieldset(
                'Bulk Updates',
                'new_status',
                'mark_as_reviewed',
                'supervisor_notes',
            ),
            Submit('submit', 'Apply Updates', css_class='btn btn-warning'),
        )

class ReportGenerationForm(forms.Form):
    """Form for generating supervisor reports"""
    
    REPORT_TYPE_CHOICES = [
        ('daily', 'Daily Report'),
        ('weekly', 'Weekly Report'),
        ('monthly', 'Monthly Report'),
        ('custom', 'Custom Period'),
    ]
    
    report_type = forms.ChoiceField(choices=REPORT_TYPE_CHOICES)
    period_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    period_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        required=False
    )
    include_individual_breakdown = forms.BooleanField(
        required=False,
        initial=True,
        label='Include individual salesperson breakdown'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'report_type',
            Row(
                Column('period_start', css_class='form-group col-md-6'),
                Column('period_end', css_class='form-group col-md-6'),
            ),
            'include_individual_breakdown',
            Submit('generate', 'Generate Report', css_class='btn btn-primary'),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        report_type = cleaned_data.get('report_type')
        period_start = cleaned_data.get('period_start')
        period_end = cleaned_data.get('period_end')
        
        if report_type == 'custom':
            if not period_start or not period_end:
                raise ValidationError('Both start and end dates are required for custom reports.')
            if period_end <= period_start:
                raise ValidationError('End date must be after start date.')
        
        return cleaned_data
