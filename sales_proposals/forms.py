from decimal import Decimal, InvalidOperation
from django import forms
from django.forms import inlineformset_factory
from .models import Proposal, ProposalItem, ProposalApprovalTier, ProposalAttachment
from customers.models import Customer
from teams.models import Team, Group, TeamMembership

from django.forms import NumberInput, TextInput, Textarea, ClearableFileInput


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
            'stock_availability',
            'payment_terms',
            'delivery_lead_time',
            'cancellation_terms',
            'include_bank_details',
            # Bank details (editable)
            'php_bank_name','php_account_name','php_account_number','php_account_type','php_branch',
            'usd_beneficiary_name','usd_beneficiary_address','usd_account_number','usd_bank_address','usd_swift_code',
            'introduction',
            'special_note',
            'closing',
        ]
        labels = {
            'stock_availability': 'Stock availability',
            'closing': 'Other terms',
            'php_bank_name': 'PHP bank name',
            'php_account_name': 'PHP account name',
            'php_account_number': 'PHP account number',
            'php_account_type': 'PHP account type',
            'php_branch': 'PHP branch',
            'usd_beneficiary_name': 'USD beneficiary name',
            'usd_beneficiary_address': 'USD beneficiary address',
            'usd_account_number': 'USD account number',
            'usd_bank_address': 'USD bank address',
            'usd_swift_code': 'USD swift code',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'valid_until': forms.DateInput(attrs={'type': 'date'}),
            'stock_availability': forms.Select(attrs={'class': 'form-select'}),
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
        fields = ['part_number', 'description', 'quantity', 'unit_cost', 'unit_price', 'warranty', 'is_optional', 'is_bundle', 'bundled_items']
        widgets = {
            'description': Textarea(attrs={'rows': 3}),
            'quantity': NumberInput(attrs={'class': 'no-spin', 'step': '1', 'min': '1', 'inputmode': 'numeric'}),
            'unit_cost': TextInput(attrs={'class': 'price-input no-spin', 'inputmode': 'decimal', 'autocomplete': 'off'}),
            'unit_price': TextInput(attrs={'class': 'price-input no-spin', 'inputmode': 'decimal', 'autocomplete': 'off'}),
            'bundled_items': Textarea(attrs={
                'rows': 5,
                'placeholder': 'Paste 2 columns from Excel (Part Number + Description), or type:\nB4YT6AV | HP IDS DSC RTX PRO 2000 8GB Ultra 9 285HX 16 inch G1i Base NB PC\n8C9M7AV | No Country of Origin Restriction',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['unit_cost'].required = False
        self.fields['bundled_items'].required = False

    def _clean_decimal_text(self, field_name):
        raw_value = self.cleaned_data.get(field_name)
        if raw_value in [None, '']:
            return None
        if isinstance(raw_value, Decimal):
            return raw_value
        normalized = str(raw_value).strip().replace(',', '')
        if normalized == '':
            return None
        try:
            return Decimal(normalized)
        except (InvalidOperation, TypeError):
            raise forms.ValidationError('Enter a valid amount.')

    def clean_unit_cost(self):
        value = self._clean_decimal_text('unit_cost')
        return value if value is not None else Decimal('0')

    def clean_unit_price(self):
        value = self._clean_decimal_text('unit_price')
        if value is None:
            raise forms.ValidationError('This field is required.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        bundled_items = (cleaned_data.get('bundled_items') or '').strip()
        cleaned_data['bundled_items'] = bundled_items

        if cleaned_data.get('is_bundle') and not bundled_items:
            self.add_error('bundled_items', 'Enter at least one bundled part number or component line.')

        return cleaned_data

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
        fields = ['file', 'include_in_email']
        widgets = {
            'file': ClearableFileInput(attrs={'multiple': False}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['include_in_email'].help_text = 'Disabled automatically for COSTING-MATRIX files.'
        if getattr(self.instance, 'pk', None) and self.instance.is_costing_matrix:
            self.fields['include_in_email'].disabled = True
            self.fields['include_in_email'].initial = False

    def clean(self):
        cleaned_data = super().clean()
        uploaded_file = cleaned_data.get('file') or getattr(self.instance, 'file', None)
        if uploaded_file:
            normalized = uploaded_file.name.rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
            stem = normalized.rsplit('.', 1)[0].strip().lower().replace('_', '-')
            if stem == 'costing-matrix':
                cleaned_data['include_in_email'] = False
                self.cleaned_data['include_in_email'] = False
        return cleaned_data

ProposalAttachmentFormSet = inlineformset_factory(
    Proposal,
    ProposalAttachment,
    form=ProposalAttachmentForm,
    fields=['file', 'include_in_email'],
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
