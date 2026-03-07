from django import forms
from .models import Proposal, ProposalItem
from django.forms import inlineformset_factory

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['reference_number', 'customer', 'date', 'valid_until', 'subject', 'introduction', 'closing', 'tax_rate', 'payment_terms', 'delivery_lead_time', 'warranty']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'introduction': forms.Textarea(attrs={'rows': 4}),
            'closing': forms.Textarea(attrs={'rows': 4}),
            'payment_terms': forms.TextInput(attrs={'placeholder': 'e.g. 30 days'}),
            'delivery_lead_time': forms.TextInput(attrs={'placeholder': 'e.g. 5-10 working days'}),
            'warranty': forms.TextInput(attrs={'placeholder': 'e.g. 1 year - Parts Warranty'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.role == 'salesperson':
             # Filter customers assigned to this salesperson
             self.fields['customer'].queryset = self.fields['customer'].queryset.filter(salesperson=user)

ProposalItemFormSet = inlineformset_factory(
    Proposal, ProposalItem,
    fields=['part_number', 'description', 'quantity', 'unit_cost', 'unit_price', 'availability'],
    widgets={
        'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Item description and specifications'}),
    },
    extra=1,
    can_delete=True
)
