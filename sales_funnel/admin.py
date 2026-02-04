from django.contrib import admin
from .models import SalesFunnel

@admin.register(SalesFunnel)
class SalesFunnelAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'salesperson', 'stage', 'retail', 'profit', 
        'date_created', 'is_active', 'is_closed'
    ]
    list_filter = ['stage', 'is_active', 'is_closed', 'date_created', 'salesperson']
    search_fields = ['company_name', 'requirement_description', 'salesperson__username']
    readonly_fields = ['created_at', 'updated_at', 'profit', 'profit_margin']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('date_created', 'company_name', 'customer', 'requirement_description')
        }),
        ('Financial Information', {
            'fields': ('cost', 'retail', 'profit', 'profit_margin')
        }),
        ('Sales Information', {
            'fields': ('stage', 'salesperson', 'expected_close_date', 'probability')
        }),
        ('Status', {
            'fields': ('is_active', 'is_closed', 'closed_date')
        }),
        ('Additional Information', {
            'fields': ('notes',)
        }),
        ('System Information', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def profit(self, obj):
        return f"₱{obj.profit:,.2f}"
    profit.short_description = 'Profit'
    
    def profit_margin(self, obj):
        return f"{obj.profit_margin:.1f}%"
    profit_margin.short_description = 'Profit Margin'
