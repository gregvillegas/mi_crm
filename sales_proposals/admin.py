from django.contrib import admin
from .models import Proposal, ProposalItem

class ProposalItemInline(admin.TabularInline):
    model = ProposalItem
    extra = 1
    readonly_fields = ('amount',)

@admin.register(Proposal)
class ProposalAdmin(admin.ModelAdmin):
    list_display = ('proposal_number', 'subject', 'customer', 'date', 'total_amount', 'status', 'created_by')
    list_filter = ('status', 'date', 'created_by')
    search_fields = ('proposal_number', 'subject', 'customer__company_name')
    inlines = [ProposalItemInline]
    readonly_fields = ('proposal_number', 'subtotal', 'tax_amount', 'total_amount', 'created_at', 'updated_at')
    
    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        form.instance.calculate_totals()
