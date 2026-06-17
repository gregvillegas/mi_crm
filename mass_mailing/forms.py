import csv
import io
from django import forms
from django.forms import ClearableFileInput, inlineformset_factory
from .models import Campaign, CampaignAsset, MediaLibraryAsset
from customers.models import Customer
from lead_generation.models import Lead


def get_allowed_leads_queryset(user):
    leads = Lead.objects.filter(is_active=True).exclude(status__in=['converted', 'lost'])
    if not user:
        return Lead.objects.none()

    if user.role == 'salesperson':
        return leads.filter(assigned_to=user)
    if user.role == 'supervisor':
        member_ids = [user.id]
        for group in user.managed_groups.all():
            member_ids.extend(group.members.values_list('user_id', flat=True))
        return leads.filter(assigned_to_id__in=set(member_ids))
    if user.role == 'teamlead':
        member_ids = [user.id]
        for group in user.led_groups.all():
            member_ids.extend(group.members.values_list('user_id', flat=True))
        return leads.filter(assigned_to_id__in=set(member_ids))
    if user.role == 'asm':
        member_ids = [user.id]
        for team in user.asm_teams.all():
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor_id:
                    member_ids.append(group.supervisor_id)
        return leads.filter(assigned_to_id__in=set(member_ids))
    if user.role == 'avp':
        member_ids = [user.id]
        for team in user.managed_teams.all():
            for group in team.groups.all():
                member_ids.extend(group.members.values_list('user_id', flat=True))
                if group.supervisor_id:
                    member_ids.append(group.supervisor_id)
        return leads.filter(assigned_to_id__in=set(member_ids))

    return leads

class CampaignForm(forms.ModelForm):
    customers = forms.ModelMultipleChoiceField(
        queryset=Customer.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        help_text="Select customers to receive this campaign. Opted-out customers will be automatically excluded."
    )
    leads = forms.ModelMultipleChoiceField(
        queryset=Lead.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={'class': 'form-control select2'}),
        help_text="Select CRM leads to receive this campaign. Converted and lost leads are excluded."
    )
    csv_file = forms.FileField(
        required=False,
        help_text="Upload CSV with columns: Company Name, Contact Name, Contact Email Address, Position",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '.csv,text/csv'})
    )
    manual_recipients = forms.CharField(
        required=False,
        help_text="Enter one recipient per line using: Company Name, Contact Name, Email Address, Position",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Batangas ABC Corp, Greg Villegas, greg@example.com, Purchasing Manager'})
    )
    csv_paste_recipients = forms.CharField(
        required=False,
        help_text="Optional fallback for CSV mode: paste one recipient per line using Company, Contact, Email, Position",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Batangas ABC Corp, Greg Villegas, greg@example.com, Purchasing Manager'})
    )

    class Meta:
        model = Campaign
        fields = [
            'name', 'subject', 'template_type', 'recipient_mode', 'body_html',
            'hero_headline', 'hero_intro', 'hero_bullet_1', 'hero_bullet_2', 'hero_bullet_3',
            'hero_cta_label', 'hero_cta_url',
            'interested_redirect_url',
            'scheduled_for', 'include_unsubscribe'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Q3 Promotion'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Email Subject'}),
            'body_html': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Dear {{ contact_name }}, ...'}),
            'template_type': forms.Select(attrs={'class': 'form-select'}),
            'recipient_mode': forms.Select(attrs={'class': 'form-select'}),
            'hero_headline': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Exclusive Offer for {{ company_name }}'}),
            'hero_intro': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Hi {{ contact_name }},\nShare your main offer here...'}),
            'hero_bullet_1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Benefit 1'}),
            'hero_bullet_2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Benefit 2'}),
            'hero_bullet_3': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Benefit 3'}),
            'hero_cta_label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Schedule a Call'}),
            'hero_cta_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'interested_redirect_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'scheduled_for': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'include_unsubscribe': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['body_html'].required = False
        if user:
            # Salespersons can only email their assigned customers
            if user.role == 'salesperson':
                self.fields['customers'].queryset = Customer.objects.filter(salesperson=user, is_active=True)
            else:
                self.fields['customers'].queryset = Customer.objects.filter(is_active=True)
            self.fields['leads'].queryset = get_allowed_leads_queryset(user)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('template_type') in ['hero_promo', 'product_launch', 'product_of_week', 'newsletter_digest'] and not cleaned.get('body_html'):
            cleaned['body_html'] = '<!-- generated by Hero Promo Builder -->'

        recipient_mode = cleaned.get('recipient_mode') or 'crm'
        if recipient_mode == 'crm':
            if not cleaned.get('customers'):
                self.add_error('customers', 'Select at least one CRM customer.')
        elif recipient_mode == 'crm_leads':
            if not cleaned.get('leads'):
                self.add_error('leads', 'Select at least one CRM lead.')
        elif recipient_mode == 'csv':
            if cleaned.get('csv_file'):
                try:
                    cleaned['parsed_csv_recipients'] = self._parse_csv(cleaned['csv_file'])
                except forms.ValidationError as e:
                    self.add_error('csv_file', e)
            elif cleaned.get('csv_paste_recipients', '').strip():
                try:
                    cleaned['parsed_csv_recipients'] = self._parse_manual(cleaned['csv_paste_recipients'], source_type='csv')
                except forms.ValidationError as e:
                    self.add_error('csv_paste_recipients', e)
            else:
                self.add_error('csv_file', 'Upload a CSV file or paste recipient rows below for CSV recipient mode.')
        elif recipient_mode == 'manual':
            manual_text = cleaned.get('manual_recipients', '').strip()
            if not manual_text:
                self.add_error('manual_recipients', 'Enter at least one manual recipient.')
            else:
                try:
                    cleaned['parsed_manual_recipients'] = self._parse_manual(manual_text, source_type='manual')
                except forms.ValidationError as e:
                    self.add_error('manual_recipients', e)
        return cleaned

    def _parse_csv(self, file):
        try:
            decoded = file.read().decode('utf-8-sig')
            file.seek(0)
        except Exception:
            raise forms.ValidationError('Unable to read CSV file. Please upload a valid UTF-8 CSV.')
        reader = csv.DictReader(io.StringIO(decoded))
        if not reader.fieldnames:
            raise forms.ValidationError('CSV file is empty or missing headers.')
        normalized = {name.strip().lower(): name for name in reader.fieldnames if name}
        required = ['company name', 'contact name', 'contact email address']
        missing = [r for r in required if r not in normalized]
        if missing:
            raise forms.ValidationError(f"CSV headers missing: {', '.join(missing)}")
        recipients = []
        seen = set()
        for idx, row in enumerate(reader, start=2):
            company = (row.get(normalized['company name']) or '').strip()
            contact = (row.get(normalized['contact name']) or '').strip()
            email = (row.get(normalized['contact email address']) or '').strip().lower()
            position = (row.get(normalized.get('position', ''), '') or '').strip() if 'position' in normalized else ''
            if not company and not contact and not email and not position:
                continue
            if not email:
                raise forms.ValidationError(f'CSV row {idx}: Contact Email Address is required.')
            forms.EmailField().clean(email)
            if email in seen:
                raise forms.ValidationError(f'CSV row {idx}: Duplicate email "{email}".')
            seen.add(email)
            recipients.append({
                'company_name': company,
                'contact_name': contact,
                'email': email,
                'position': position,
                'source_type': 'csv',
            })
        if not recipients:
            raise forms.ValidationError('CSV file contains no valid recipients.')
        return recipients

    def _parse_manual(self, manual_text, source_type='manual'):
        recipients = []
        seen = set()
        for idx, line in enumerate(manual_text.splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split(',')]
            if len(parts) < 3:
                raise forms.ValidationError(f'Line {idx}: use Company Name, Contact Name, Email Address, Position.')
            company, contact, email = parts[:3]
            position = parts[3] if len(parts) > 3 else ''
            email = email.lower()
            forms.EmailField().clean(email)
            if email in seen:
                raise forms.ValidationError(f'Line {idx}: Duplicate email "{email}".')
            seen.add(email)
            recipients.append({
                'company_name': company,
                'contact_name': contact,
                'email': email,
                'position': position,
                'source_type': source_type,
            })
        if not recipients:
            raise forms.ValidationError('Enter at least one valid recipient.')
        return recipients


class CampaignAssetForm(forms.ModelForm):
    class Meta:
        model = CampaignAsset
        fields = ['file', 'display_name', 'embed_inline', 'sort_order']
        widgets = {
            'file': ClearableFileInput(attrs={'accept': 'image/*'}),
            'display_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional image label'}),
            'embed_inline': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file
        content_type = getattr(file, 'content_type', '') or ''
        if not content_type.startswith('image/'):
            raise forms.ValidationError('Only image files are supported for campaign embeds.')
        return file


CampaignAssetFormSet = inlineformset_factory(
    Campaign,
    CampaignAsset,
    form=CampaignAssetForm,
    fields=['file', 'display_name', 'embed_inline', 'sort_order'],
    extra=1,
    can_delete=True
)


class MediaLibraryAssetForm(forms.ModelForm):
    class Meta:
        model = MediaLibraryAsset
        fields = ['title', 'file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. April Promo Banner'}),
            'file': ClearableFileInput(attrs={'accept': 'image/*', 'class': 'form-control'}),
        }

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if not file:
            return file
        content_type = getattr(file, 'content_type', '') or ''
        if not content_type.startswith('image/'):
            raise forms.ValidationError('Only image files are supported in the media library.')
        return file

class UnsubscribeForm(forms.Form):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control', 'readonly': 'readonly'}))
    reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional: Tell us why you are unsubscribing...'})
    )
