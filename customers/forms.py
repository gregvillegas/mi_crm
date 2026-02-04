from django import forms
from .models import Customer, DelinquencyRecord
from users.models import User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'company_name', 'contact_person_name', 'contact_person_position', 'email', 'phone_number', 'address',
            'industry', 'territory', 'is_vip', 'is_active', 'salesperson'
        ]
        widgets = {
            'is_vip': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'company_name': 'Company Name',
            'contact_person_name': 'Contact Person Name',
            'contact_person_position': 'Position/Title',
            'is_vip': 'VIP/Millionaire Account',
            'is_active': 'Active Customer',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active salespeople in the dropdown
        self.fields['salesperson'].queryset = User.objects.filter(
            role='salesperson', 
            is_active=True
        )
        
        # Add CSS classes and help text
        self.fields['industry'].widget.attrs.update({'class': 'form-select'})
        self.fields['territory'].widget.attrs.update({'class': 'form-select'})
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h5 class="mb-3">Basic Information</h5>'),
            Row(
                Column('company_name', css_class='form-group col-md-6 mb-3'),
                Column('contact_person_name', css_class='form-group col-md-6 mb-3'),
            ),
            'contact_person_position',
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('phone_number', css_class='form-group col-md-6 mb-3'),
            ),
            'address',
            
            HTML('<h5 class="mb-3 mt-4">Business Information</h5>'),
            Row(
                Column('industry', css_class='form-group col-md-6 mb-3'),
                Column('territory', css_class='form-group col-md-6 mb-3'),
            ),
            
            HTML('<h5 class="mb-3 mt-4">Status & Assignment</h5>'),
            Row(
                Column(
                    HTML('<div class="form-check mb-3">'),
                    'is_vip',
                    HTML('</div>'),
                    css_class='col-md-6'
                ),
                Column(
                    HTML('<div class="form-check mb-3">'),
                    'is_active',
                    HTML('</div>'),
                    css_class='col-md-6'
                ),
            ),
            'salesperson',
            HTML('<br>'),
            Submit('submit', 'Save Customer', css_class='btn btn-primary')
        )

class SalespersonCustomerForm(forms.ModelForm):
    """Form for salespeople to add new customers - automatically assigns them as salesperson"""
    class Meta:
        model = Customer
        fields = [
            'company_name', 'contact_person_name', 'contact_person_position', 'email', 'phone_number', 'address',
            'industry', 'territory'
        ]
        labels = {
            'company_name': 'Company Name',
            'contact_person_name': 'Contact Person Name',
            'contact_person_position': 'Position/Title',
        }

    def __init__(self, *args, **kwargs):
        self.salesperson = kwargs.pop('salesperson', None)
        super().__init__(*args, **kwargs)
        
        # Add CSS classes and help text
        self.fields['industry'].widget.attrs.update({'class': 'form-select'})
        self.fields['territory'].widget.attrs.update({'class': 'form-select'})
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<div class="alert alert-info"><i class="fas fa-info-circle"></i> You will be automatically assigned as the salesperson for this customer.</div>'),
            HTML('<h5 class="mb-3">Basic Information</h5>'),
            Row(
                Column('company_name', css_class='form-group col-md-6 mb-3'),
                Column('contact_person_name', css_class='form-group col-md-6 mb-3'),
            ),
            'contact_person_position',
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('phone_number', css_class='form-group col-md-6 mb-3'),
            ),
            'address',
            
            HTML('<h5 class="mb-3 mt-4">Business Information</h5>'),
            Row(
                Column('industry', css_class='form-group col-md-6 mb-3'),
                Column('territory', css_class='form-group col-md-6 mb-3'),
            ),
            HTML('<br>'),
            Submit('submit', 'Add Customer', css_class='btn btn-primary')
        )
    
    def save(self, commit=True):
        customer = super().save(commit=False)
        # Automatically assign the salesperson
        if self.salesperson:
            customer.salesperson = self.salesperson
        # New customers are active by default, not VIP
        customer.is_active = True
        customer.is_vip = False
        
        if commit:
            customer.save()
            # Log the customer creation
            from .models import CustomerHistory
            CustomerHistory.log_customer_change(
                customer=customer,
                action='created',
                description=f'New customer added by salesperson {self.salesperson.username if self.salesperson else "Unknown"}',
                changed_by=self.salesperson
            )
        return customer

class DelinquencyRecordForm(forms.ModelForm):
    class Meta:
        model = DelinquencyRecord
        fields = ['customer', 'salesperson', 'status', 'tin_number', 'amount_due', 'due_date', 'last_payment_date', 'remarks']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'last_payment_date': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('customer', css_class='col-md-6'),
                Column('salesperson', css_class='col-md-6'),
            ),
            Row(
                Column('status', css_class='col-md-3'),
                Column('tin_number', css_class='col-md-3'),
                Column('amount_due', css_class='col-md-3'),
                Column('due_date', css_class='col-md-3'),
            ),
            Row(
                Column('last_payment_date', css_class='col-md-4'),
            ),
            'remarks',
            Submit('submit', 'Save Record', css_class='btn btn-primary')
        )
