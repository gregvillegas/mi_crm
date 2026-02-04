from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    LeadSource, Lead, LeadActivity, LeadScoring, 
    ConversionTracking, LeadNurturingCampaign
)

@admin.register(LeadSource)
class LeadSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'total_leads', 'converted_leads', 'conversion_rate_display', 'cost_per_lead', 'is_active']
    list_filter = ['source_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at']
    
    def conversion_rate_display(self, obj):
        return f"{obj.conversion_rate:.1f}%"
    conversion_rate_display.short_description = 'Conversion Rate'
    
    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('leads')


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        'full_name', 'company_name', 'email', 'status_badge', 'priority_badge', 
        'lead_score', 'source', 'assigned_to', 'created_at'
    ]
    list_filter = [
        'status', 'priority', 'source', 'is_qualified', 'assigned_to',
        'industry', 'territory', 'created_at'
    ]
    search_fields = ['first_name', 'last_name', 'email', 'company_name', 'phone_number']
    readonly_fields = ['lead_score', 'days_as_lead', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number', 'company_name', 'job_title')
        }),
        ('Business Information', {
            'fields': ('industry', 'territory', 'company_size', 'annual_revenue', 'address', 'city')
        }),
        ('Lead Management', {
            'fields': ('status', 'priority', 'source', 'assigned_to', 'is_qualified', 'is_active')
        }),
        ('Requirements & Interest', {
            'fields': ('initial_interest', 'requirements', 'budget_range', 'timeline')
        }),
        ('Scoring & Conversion', {
            'fields': ('lead_score', 'converted_to_customer', 'conversion_date', 'conversion_value')
        }),
        ('Timeline', {
            'fields': ('first_contact_date', 'last_contact_date', 'next_follow_up_date', 'expected_close_date')
        }),
        ('Additional Info', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('System Info', {
            'fields': ('days_as_lead', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_badge(self, obj):
        color_map = {
            'new': 'primary',
            'contacted': 'info', 
            'qualified': 'success',
            'proposal_sent': 'warning',
            'negotiating': 'warning',
            'converted': 'success',
            'lost': 'danger',
            'unqualified': 'secondary'
        }
        color = color_map.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def priority_badge(self, obj):
        color_map = {
            'low': 'secondary',
            'medium': 'primary', 
            'high': 'warning',
            'hot': 'danger'
        }
        color = color_map.get(obj.priority, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Priority'
    
    actions = ['calculate_lead_scores', 'mark_as_qualified', 'mark_as_unqualified']
    
    def calculate_lead_scores(self, request, queryset):
        count = 0
        for lead in queryset:
            lead.calculate_lead_score()
            count += 1
        self.message_user(request, f"Recalculated lead scores for {count} leads.")
    calculate_lead_scores.short_description = "Recalculate lead scores"
    
    def mark_as_qualified(self, request, queryset):
        count = queryset.update(is_qualified=True)
        self.message_user(request, f"Marked {count} leads as qualified.")
    mark_as_qualified.short_description = "Mark as qualified"
    
    def mark_as_unqualified(self, request, queryset):
        count = queryset.update(is_qualified=False)
        self.message_user(request, f"Marked {count} leads as unqualified.")
    mark_as_unqualified.short_description = "Mark as unqualified"


@admin.register(LeadActivity)
class LeadActivityAdmin(admin.ModelAdmin):
    list_display = [
        'lead', 'activity_type', 'title', 'outcome', 'performed_by', 
        'follow_up_required', 'created_at'
    ]
    list_filter = [
        'activity_type', 'outcome', 'follow_up_required', 
        'performed_by', 'created_at'
    ]
    search_fields = ['lead__first_name', 'lead__last_name', 'title', 'description']
    readonly_fields = ['created_at']
    
    fieldsets = (
        ('Activity Info', {
            'fields': ('lead', 'activity_type', 'title', 'description', 'performed_by')
        }),
        ('Outcome & Follow-up', {
            'fields': ('outcome', 'follow_up_required', 'follow_up_date')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        })
    )


@admin.register(LeadScoring)
class LeadScoringAdmin(admin.ModelAdmin):
    list_display = [
        'lead', 'total_score', 'demographic_score', 'company_score', 
        'behavioral_score', 'engagement_score', 'fit_score', 'last_calculated'
    ]
    list_filter = ['last_calculated']
    search_fields = ['lead__first_name', 'lead__last_name', 'lead__company_name']
    readonly_fields = ['total_score', 'last_calculated']


@admin.register(ConversionTracking)
class ConversionTrackingAdmin(admin.ModelAdmin):
    list_display = [
        'lead', 'customer', 'converted_by', 'conversion_date', 
        'days_to_convert', 'conversion_value', 'roi_display'
    ]
    list_filter = ['conversion_date', 'converted_by']
    search_fields = [
        'lead__first_name', 'lead__last_name', 'customer__company_name',
        'customer__contact_person_name'
    ]
    readonly_fields = ['conversion_date', 'days_to_convert']
    
    def roi_display(self, obj):
        roi = obj.roi
        if roi is not None:
            return f"{roi:.1f}%"
        return "N/A"
    roi_display.short_description = 'ROI'


@admin.register(LeadNurturingCampaign)
class LeadNurturingCampaignAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'target_status', 'target_score_range', 'follow_up_days', 
        'auto_assign_salesperson', 'is_active', 'created_at'
    ]
    list_filter = ['target_status', 'is_active', 'auto_assign_salesperson', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def target_score_range(self, obj):
        return f"{obj.target_score_min}-{obj.target_score_max}"
    target_score_range.short_description = 'Score Range'
    
    fieldsets = (
        ('Campaign Info', {
            'fields': ('name', 'description', 'created_by', 'is_active')
        }),
        ('Targeting', {
            'fields': ('target_status', 'target_score_min', 'target_score_max')
        }),
        ('Campaign Settings', {
            'fields': ('email_template', 'follow_up_days', 'auto_assign_salesperson')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )
