from django import forms
from .models import Proposal, ProposalItem
from django.forms import inlineformset_factory

class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = ['reference_number', 'customer', 'date', 'valid_until', 'subject', 'currency', 'exchange_rate', 'introduction', 'special_note', 'closing', 'tax_type', 'tax_rate', 'payment_terms', 'delivery_lead_time', 'warranty', 'cancellation_terms', 'include_bank_details']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'introduction': forms.Textarea(attrs={'rows': 4}),
            'special_note': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Optional special note (e.g. PRICE SUBJECT TO CHANGE...)'}),
            'closing': forms.Textarea(attrs={'rows': 4}),
            'payment_terms': forms.TextInput(attrs={'placeholder': 'e.g. 30 days'}),
            'delivery_lead_time': forms.TextInput(attrs={'placeholder': 'e.g. 5-10 working days'}),
            'warranty': forms.TextInput(attrs={'placeholder': 'e.g. 1 year - Parts Warranty'}),
            'tax_type': forms.Select(attrs={'class': 'form-select'}),
            'cancellation_terms': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user and user.role == 'salesperson':
             # Filter customers assigned to this salesperson
             self.fields['customer'].queryset = self.fields['customer'].queryset.filter(salesperson=user)

class ProposalItemForm(forms.ModelForm):
    class Meta:
        model = ProposalItem
        fields = ['part_number', 'description', 'quantity', 'unit_cost', 'unit_price', 'availability']
        labels = {
            'unit_price': 'Unit SRP',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Item description and specifications'}),
            'quantity': forms.NumberInput(attrs={'step': '1', 'min': '1', 'class': 'text-end'}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00', 'class': 'no-spin text-end'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'placeholder': '0.00', 'class': 'no-spin text-end'}),
        }

ProposalItemFormSet = inlineformset_factory(
    Proposal, ProposalItem,
    form=ProposalItemForm,
    extra=1,
    can_delete=True
)
