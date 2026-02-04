from django.contrib import admin
from .models import Customer, CustomerHistory, CustomerBackup, DelinquencyRecord

@admin.register(CustomerHistory)
class CustomerHistoryAdmin(admin.ModelAdmin):
    list_display = ('customer', 'action', 'changed_by', 'salesperson_at_time', 'timestamp')
    list_filter = ('action', 'timestamp', 'changed_by', 'salesperson_at_time')
    search_fields = ('customer__company_name', 'description', 'changed_by__username')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('customer', 'action', 'description')
        }),
        ('Attribution', {
            'fields': ('changed_by', 'salesperson_at_time')
        }),
        ('Change Data', {
            'fields': ('old_value', 'new_value'),
            'classes': ('collapse',)
        }),
        ('Tracking', {
            'fields': ('timestamp', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person_name', 'email', 'is_vip', 'is_active', 'salesperson')
    list_filter = ('is_vip', 'is_active', 'industry', 'territory')
    search_fields = ('company_name', 'contact_person_name', 'email')
    
@admin.register(CustomerBackup)
class CustomerBackupAdmin(admin.ModelAdmin):
    list_display = ('customer', 'reason', 'changed_by', 'created_at')
    list_filter = ('created_at', 'changed_by')
    search_fields = ('customer__company_name', 'reason')

@admin.register(DelinquencyRecord)
class DelinquencyRecordAdmin(admin.ModelAdmin):
    list_display = ('customer', 'tin_number', 'status', 'amount_due', 'due_date', 'salesperson', 'updated_at')
    list_filter = ('status', 'salesperson')
    search_fields = ('customer__company_name', 'salesperson__username', 'tin_number', 'remarks')
