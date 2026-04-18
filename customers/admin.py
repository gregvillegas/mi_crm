from django.contrib import admin
from .models import Customer, CustomerHistory, CustomerBackup, DelinquencyRecord, DelinquentCustomer, CustomerContact

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

class CustomerContactInline(admin.TabularInline):
    model = CustomerContact
    extra = 0
    max_num = 4
    fields = ('name','position','email','phone','is_primary')
    classes = ['collapse']

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'contact_person_name', 'email', 'is_millionaire_account', 'auto_inactive_flag', 'is_active', 'salesperson')
    list_filter = ('is_millionaire_account', 'auto_inactive_flag', 'is_active', 'industry', 'territory')
    search_fields = ('company_name', 'contact_person_name', 'email')
    inlines = [CustomerContactInline]
    
@admin.register(CustomerBackup)
class CustomerBackupAdmin(admin.ModelAdmin):
    list_display = ('customer', 'reason', 'changed_by', 'created_at')
    list_filter = ('created_at', 'changed_by')
    search_fields = ('customer__company_name', 'reason')

@admin.register(DelinquentCustomer)
class DelinquentCustomerAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'assigned_ae', 'email', 'created_at', 'updated_at')
    search_fields = ('company_name', 'assigned_ae', 'email')
    ordering = ('company_name',)

@admin.register(DelinquencyRecord)
class DelinquencyRecordAdmin(admin.ModelAdmin):
    list_display = ('customer', 'tin_number', 'status', 'partner_name', 'date_delivered', 'salesperson', 'updated_at')
    list_filter = ('status', 'salesperson')
    search_fields = ('customer__company_name', 'salesperson__username', 'tin_number', 'remarks')
