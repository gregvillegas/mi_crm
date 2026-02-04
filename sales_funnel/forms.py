from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import SalesFunnel
from customers.models import Customer
from users.models import User

class SalesFunnelForm(forms.ModelForm):
    class Meta:
        model = SalesFunnel
        fields = [
            'date_created', 'company_name', 'requirement_description',
            'cost', 'retail', 'stage', 'customer', 'expected_close_date',
            'probability', 'notes'
        ]
        widgets = {
            'date_created': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter company name'
            }),
            'requirement_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Describe the customer requirements...'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'retail': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'stage': forms.Select(attrs={
                'class': 'form-select'
            }),
            'customer': forms.Select(attrs={
                'class': 'form-select'
            }),
            'expected_close_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'probability': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '5'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Additional notes (optional)...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Set today as default date
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date_created'].initial = timezone.now().date()
        
        # Filter customers based on user access
        if user:
            if user.role == 'salesperson':
                # Salespeople can only see their own customers
                self.fields['customer'].queryset = Customer.objects.filter(
                    salesperson=user, is_active=True
                ).order_by('company_name')
            elif user.role in ['supervisor', 'teamlead', 'asm', 'avp']:
                # Managers can see customers in their scope
                # For now, show all active customers - this can be refined based on hierarchy
                self.fields['customer'].queryset = Customer.objects.filter(
                    is_active=True
                ).order_by('company_name')
            else:
                # Admins and executives see all
                self.fields['customer'].queryset = Customer.objects.filter(
                    is_active=True
                ).order_by('company_name')
        
        # Make customer field optional
        self.fields['customer'].empty_label = "-- Select existing customer (optional) --"
        
        # Add helpful labels
        self.fields['cost'].label = "Cost (₱)"
        self.fields['retail'].label = "Retail Price (₱)"
        self.fields['probability'].label = "Win Probability (%)"
        
    def clean(self):
        cleaned_data = super().clean()
        cost = cleaned_data.get('cost')
        retail = cleaned_data.get('retail')
        probability = cleaned_data.get('probability')
        
        # Validate cost vs retail
        if cost is not None and retail is not None:
            if retail < cost:
                raise forms.ValidationError("Retail price cannot be less than cost.")
        
        # Validate probability range
        if probability is not None:
            if probability < 0 or probability > 100:
                raise forms.ValidationError("Probability must be between 0 and 100.")
        
        return cleaned_data


from teams.models import Team, Group, TeamMembership


class FunnelFilterForm(forms.Form):
    """Form for filtering funnel entries on dashboard"""
    stage = forms.ChoiceField(
        choices=[('', 'All Stages')] + SalesFunnel.FUNNEL_STAGES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    salesperson = forms.ModelChoiceField(
        queryset=User.objects.none(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )
    min_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'step': '0.01', 'placeholder': '₱0.00'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control form-control-sm'
        })
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        qs = User.objects.filter(role='salesperson', is_active=True)
        if user:
            if user.role == 'salesperson':
                qs = User.objects.filter(id=user.id)
            elif user.role == 'supervisor':
                groups = Group.objects.filter(supervisor=user)
                salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
                qs = User.objects.filter(id__in=salespeople_ids)
            elif user.role == 'teamlead':
                teamlead_groups = Group.objects.filter(teamlead=user)
                salespeople_ids = TeamMembership.objects.filter(group__in=teamlead_groups).values_list('user_id', flat=True)
                qs = User.objects.filter(id__in=salespeople_ids)
            elif user.role == 'asm':
                asm_teams = user.asm_teams.all()
                groups = Group.objects.filter(team__in=asm_teams)
                salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
                qs = User.objects.filter(id__in=salespeople_ids)
            elif user.role == 'avp':
                teams = Team.objects.filter(avp=user)
                groups = Group.objects.filter(team__in=teams)
                salespeople_ids = TeamMembership.objects.filter(group__in=groups).values_list('user_id', flat=True)
                qs = User.objects.filter(id__in=salespeople_ids)
            else:
                qs = User.objects.filter(role='salesperson', is_active=True)
        self.fields['salesperson'].queryset = qs.order_by('first_name', 'last_name')
        self.fields['salesperson'].empty_label = '-- All Salespeople --'


class BulkUpdateStageForm(forms.Form):
    """Form for bulk updating funnel stages"""
    entries = forms.CharField(widget=forms.HiddenInput())
    new_stage = forms.ChoiceField(
        choices=SalesFunnel.FUNNEL_STAGES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
