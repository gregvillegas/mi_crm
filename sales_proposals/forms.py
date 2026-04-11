from django import forms
from django.forms import inlineformset_factory
from .models import Proposal, ProposalItem, ProposalApprovalTier, ProposalAttachment
from customers.models import Customer
from teams.models import Team, Group, TeamMembership
from django.forms import NumberInput, HiddenInput, TextInput, ClearableFileInput


class ProposalForm(forms.ModelForm):
    class Meta:
        model = Proposal
        fields = [
            'customer',
            'contact_name',
            'contact_email',
            'contact_phone',
            'subject',
            'currency',
            'exchange_rate',
            'date',
            'valid_until',
            'payment_terms',
            'delivery_lead_time',
            'cancellation_terms',
            'include_bank_details',
            # Bank details (editable)
            'php_bank_name','php_account_name','php_account_number','php_account_type','php_branch',
            'usd_beneficiary_name','usd_beneficiary_address','usd_account_number','usd_bank_address','usd_swift_code',
            # Price Validity options
            'validity_subject_to_prior_sale','validity_availability_at_order',
            'introduction',
            'special_note',
            'closing',
            'tax_type',
            'tax_rate',
        ]
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'introduction': forms.Textarea(attrs={'rows': 3}),
            'special_note': forms.Textarea(attrs={'rows': 1}),
            'closing': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        qs = Customer.objects.filter(is_active=True)
        role = getattr(self.user, 'role', None) if self.user else None
        if role == 'salesperson':
            qs = qs.filter(salesperson=self.user)
        elif role == 'supervisor':
            groups = Group.objects.filter(supervisor=self.user)
            sp_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            qs = qs.filter(salesperson_id__in=sp_ids)
        elif role == 'teamlead':
            groups = Group.objects.filter(teamlead=self.user)
            sp_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            qs = qs.filter(salesperson_id__in=sp_ids)
        elif role == 'asm':
            asm_teams = getattr(self.user, 'asm_teams', None)
            team_qs = asm_teams.all() if asm_teams is not None else Team.objects.none()
            groups = Group.objects.filter(team__in=team_qs)
            sp_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            qs = qs.filter(salesperson_id__in=sp_ids)
        elif role == 'avp':
            teams = Team.objects.filter(avp=self.user)
            groups = Group.objects.filter(team__in=teams)
            sp_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
            qs = qs.filter(salesperson_id__in=sp_ids)
        self.fields['customer'].queryset = qs


class ProposalItemForm(forms.ModelForm):
    class Meta:
        model = ProposalItem
        fields = ['part_number', 'description', 'quantity', 'unit_cost', 'unit_price', 'warranty', 'margin_pct']
        widgets = {
            'quantity': NumberInput(attrs={'class': 'no-spin', 'step': '1', 'min': '1', 'inputmode': 'numeric'}),
            'unit_cost': NumberInput(attrs={'class': 'no-spin', 'step': '0.01', 'inputmode': 'decimal'}),
            'unit_price': NumberInput(attrs={'class': 'no-spin', 'step': '0.01', 'inputmode': 'decimal'}),
            'margin_pct': HiddenInput(),
        }

ProposalItemFormSet = inlineformset_factory(
    Proposal,
    ProposalItem,
    form=ProposalItemForm,
    extra=1,
    can_delete=True
)

class ProposalAttachmentForm(forms.ModelForm):
    class Meta:
        model = ProposalAttachment
        fields = ['file', 'display_name', 'include_in_email']
        widgets = {
            'file': ClearableFileInput(attrs={'multiple': False}),
            'display_name': TextInput(attrs={'placeholder': 'Optional display name'}),
        }

ProposalAttachmentFormSet = inlineformset_factory(
    Proposal,
    ProposalAttachment,
    form=ProposalAttachmentForm,
    fields=['file', 'display_name', 'include_in_email'],
    extra=1,
    can_delete=True
)

class ProposalApprovalTierForm(forms.ModelForm):
    class Meta:
        model = ProposalApprovalTier
        fields = ['name', 'min_amount_php', 'max_amount_php', 'chain', 'order', 'active']
        widgets = {
            'chain': forms.TextInput(attrs={'placeholder': 'supervisor,asm,avp_or_gm'}),
        }


class ProposalApprovalTierImportForm(forms.Form):
    file = forms.FileField()
    replace_existing = forms.BooleanField(required=False, initial=False)
