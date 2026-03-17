from django import forms
from .models import Campaign
from customers.models import Customer

class CampaignForm(forms.ModelForm):
    customers = forms.ModelMultipleChoiceField(
        queryset=Customer.objects.none(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        help_text="Select customers to receive this campaign. Opted-out customers will be automatically excluded."
    )

    class Meta:
        model = Campaign
        fields = ['name', 'subject', 'body_html', 'scheduled_for', 'include_unsubscribe']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q3 Promotion'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Subject'}),
            'body_html': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Dear {{ contact_name }}, ...'}),
            'scheduled_for': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'include_unsubscribe': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            # Salespersons can only email their assigned customers
            if user.role == 'salesperson':
                self.fields['customers'].queryset = Customer.objects.filter(salesperson=user, is_active=True)
            else:
                self.fields['customers'].queryset = Customer.objects.filter(is_active=True)

class UnsubscribeForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional: Tell us why you are unsubscribing...'})
    )
