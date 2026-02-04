from django import forms
from django.forms import inlineformset_factory
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Field
from crispy_forms.bootstrap import FormActions
from .models import Lead, LeadSource, LeadActivity, ConversionTracking, LeadNurturingCampaign
from customers.models import Customer
from users.models import User

class LeadForm(forms.ModelForm):
    """Form for creating and editing leads"""
    
    class Meta:
        model = Lead
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', 'company_name', 'job_title',
            'address', 'city', 'territory', 'industry', 'company_size', 'annual_revenue',
            'source', 'assigned_salesperson', 'priority', 'initial_interest', 'requirements',
            'budget_range', 'timeline', 'next_follow_up_date', 'expected_close_date', 'notes'
        ]
        widgets = {
            'initial_interest': forms.Textarea(attrs={'rows': 3}),
            'requirements': forms.Textarea(attrs={'rows': 3}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
            'next_follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expected_close_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Filter salesperson choices based on user's role and permissions
        if user:
            if user.role in ['salesperson']:
                # Salespeople can only assign to themselves
                self.fields['assigned_salesperson'].queryset = User.objects.filter(id=user.id)
            elif user.role in ['supervisor', 'asm', 'avp']:
                # Supervisors can assign to their team members
                team_members = User.objects.filter(
                    team_membership__group__in=user.supervised_groups.all(),
                    role='salesperson'
                )
                self.fields['assigned_salesperson'].queryset = team_members
            else:
                # Admins and executives see all salespeople
                self.fields['assigned_salesperson'].queryset = User.objects.filter(
                    role='salesperson', is_active=True
                )
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            HTML('<h4 class="text-primary"><i class="fas fa-user-plus"></i> Lead Information</h4>'),
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-0'),
                Column('last_name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-0'),
                Column('phone_number', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('company_name', css_class='form-group col-md-8 mb-0'),
                Column('job_title', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            HTML('<hr><h5 class="text-secondary"><i class="fas fa-building"></i> Business Details</h5>'),
            Row(
                Column('industry', css_class='form-group col-md-6 mb-0'),
                Column('territory', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('company_size', css_class='form-group col-md-6 mb-0'),
                Column('annual_revenue', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            'city',
            HTML('<hr><h5 class="text-info"><i class="fas fa-chart-line"></i> Lead Management</h5>'),
            Row(
                Column('source', css_class='form-group col-md-4 mb-0'),
                Column('assigned_salesperson', css_class='form-group col-md-4 mb-0'),
                Column('priority', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('budget_range', css_class='form-group col-md-6 mb-0'),
                Column('timeline', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            HTML('<hr><h5 class="text-warning"><i class="fas fa-clipboard-list"></i> Requirements & Timeline</h5>'),
            'initial_interest',
            'requirements',
            Row(
                Column('next_follow_up_date', css_class='form-group col-md-6 mb-0'),
                Column('expected_close_date', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'notes',
            FormActions(
                Submit('submit', 'Save Lead', css_class='btn-primary'),
                HTML('<a href="{% url "lead_generation:lead_list" %}" class="btn btn-secondary">Cancel</a>')
            )
        )


class LeadActivityForm(forms.ModelForm):\n    \"\"\"Form for logging lead activities\"\"\"\n    \n    class Meta:\n        model = LeadActivity\n        fields = [\n            'activity_type', 'title', 'description', 'outcome', \n            'follow_up_required', 'follow_up_date'\n        ]\n        widgets = {\n            'description': forms.Textarea(attrs={'rows': 4}),\n            'follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),\n        }\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h5><i class=\"fas fa-tasks\"></i> Log Activity</h5>'),\n            Row(\n                Column('activity_type', css_class='form-group col-md-6 mb-0'),\n                Column('outcome', css_class='form-group col-md-6 mb-0'),\n                css_class='form-row'\n            ),\n            'title',\n            'description',\n            HTML('<div class=\"form-check mt-3\">'),\n            Field('follow_up_required', css_class='form-check-input'),\n            HTML('</div>'),\n            'follow_up_date',\n            FormActions(\n                Submit('submit', 'Log Activity', css_class='btn-success'),\n                HTML('<button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>')\n            )\n        )


class LeadSourceForm(forms.ModelForm):\n    \"\"\"Form for managing lead sources\"\"\"\n    \n    class Meta:\n        model = LeadSource\n        fields = ['name', 'source_type', 'description', 'cost_per_lead', 'is_active']\n        widgets = {\n            'description': forms.Textarea(attrs={'rows': 3}),\n            'cost_per_lead': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),\n        }\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h4><i class=\"fas fa-bullhorn\"></i> Lead Source Details</h4>'),\n            Row(\n                Column('name', css_class='form-group col-md-8 mb-0'),\n                Column('source_type', css_class='form-group col-md-4 mb-0'),\n                css_class='form-row'\n            ),\n            'description',\n            Row(\n                Column('cost_per_lead', css_class='form-group col-md-6 mb-0'),\n                Column('is_active', css_class='form-group col-md-6 mb-0'),\n                css_class='form-row'\n            ),\n            FormActions(\n                Submit('submit', 'Save Source', css_class='btn-primary'),\n                HTML('<a href=\"{% url \"lead_generation:source_list\" %}\" class=\"btn btn-secondary\">Cancel</a>')\n            )\n        )


class ConversionForm(forms.ModelForm):\n    \"\"\"Form for converting leads to customers\"\"\"\n    \n    create_sales_funnel_entry = forms.BooleanField(\n        required=False,\n        initial=True,\n        help_text=\"Create a sales funnel entry when converting this lead\"\n    )\n    \n    sales_funnel_stage = forms.ChoiceField(\n        choices=[],\n        required=False,\n        help_text=\"Initial sales funnel stage for the new entry\"\n    )\n    \n    class Meta:\n        model = ConversionTracking\n        fields = ['conversion_value', 'notes']\n        widgets = {\n            'conversion_value': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),\n            'notes': forms.Textarea(attrs={'rows': 3}),\n        }\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        # Import here to avoid circular imports\n        from sales_funnel.models import SalesFunnel\n        \n        self.fields['sales_funnel_stage'].choices = SalesFunnel.FUNNEL_STAGES\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h4><i class=\"fas fa-exchange-alt\"></i> Convert Lead to Customer</h4>'),\n            HTML('<div class=\"alert alert-info\"><i class=\"fas fa-info-circle\"></i> This will create a new customer record and optionally add them to the sales funnel.</div>'),\n            'conversion_value',\n            HTML('<div class=\"form-check mt-3\">'),\n            Field('create_sales_funnel_entry', css_class='form-check-input'),\n            HTML('</div>'),\n            'sales_funnel_stage',\n            'notes',\n            FormActions(\n                Submit('submit', 'Convert to Customer', css_class='btn-success'),\n                HTML('<a href=\"javascript:history.back()\" class=\"btn btn-secondary\">Cancel</a>')\n            )\n        )\n\n\nclass LeadStatusUpdateForm(forms.ModelForm):\n    \"\"\"Quick form for updating lead status and priority\"\"\"\n    \n    class Meta:\n        model = Lead\n        fields = ['status', 'priority', 'is_qualified', 'next_follow_up_date']\n        widgets = {\n            'next_follow_up_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),\n        }\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h5><i class=\"fas fa-edit\"></i> Quick Status Update</h5>'),\n            Row(\n                Column('status', css_class='form-group col-md-6 mb-0'),\n                Column('priority', css_class='form-group col-md-6 mb-0'),\n                css_class='form-row'\n            ),\n            Row(\n                Column('is_qualified', css_class='form-group col-md-6 mb-0'),\n                Column('next_follow_up_date', css_class='form-group col-md-6 mb-0'),\n                css_class='form-row'\n            ),\n            FormActions(\n                Submit('submit', 'Update Status', css_class='btn-primary'),\n                HTML('<button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>')\n            )\n        )\n\n\nclass LeadFilterForm(forms.Form):\n    \"\"\"Form for filtering leads on the dashboard\"\"\"\n    \n    STATUS_CHOICES = [('', 'All Statuses')] + Lead.STATUS_CHOICES\n    PRIORITY_CHOICES = [('', 'All Priorities')] + Lead.PRIORITY_CHOICES\n    \n    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)\n    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False)\n    source = forms.ModelChoiceField(queryset=LeadSource.objects.filter(is_active=True), required=False, empty_label=\"All Sources\")\n    assigned_salesperson = forms.ModelChoiceField(queryset=User.objects.filter(role='salesperson', is_active=True), required=False, empty_label=\"All Salespeople\")\n    \n    score_min = forms.IntegerField(\n        required=False, \n        widget=forms.NumberInput(attrs={'min': '0', 'max': '100', 'placeholder': 'Min Score'})\n    )\n    score_max = forms.IntegerField(\n        required=False, \n        widget=forms.NumberInput(attrs={'min': '0', 'max': '100', 'placeholder': 'Max Score'})\n    )\n    \n    created_from = forms.DateField(\n        required=False,\n        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'From Date'})\n    )\n    created_to = forms.DateField(\n        required=False,\n        widget=forms.DateInput(attrs={'type': 'date', 'placeholder': 'To Date'})\n    )\n    \n    def __init__(self, *args, **kwargs):\n        user = kwargs.pop('user', None)\n        super().__init__(*args, **kwargs)\n        \n        # Filter salesperson choices based on user permissions\n        if user and user.role in ['supervisor', 'asm', 'avp']:\n            # Show only team members for supervisors\n            team_members = User.objects.filter(\n                team_membership__group__in=user.supervised_groups.all(),\n                role='salesperson'\n            )\n            self.fields['assigned_salesperson'].queryset = team_members\n        \n        self.helper = FormHelper()\n        self.helper.form_method = 'get'\n        self.helper.layout = Layout(\n            Row(\n                Column('status', css_class='form-group col-md-3 mb-0'),\n                Column('priority', css_class='form-group col-md-3 mb-0'),\n                Column('source', css_class='form-group col-md-3 mb-0'),\n                Column('assigned_salesperson', css_class='form-group col-md-3 mb-0'),\n                css_class='form-row'\n            ),\n            Row(\n                Column('score_min', css_class='form-group col-md-2 mb-0'),\n                Column('score_max', css_class='form-group col-md-2 mb-0'),\n                Column('created_from', css_class='form-group col-md-4 mb-0'),\n                Column('created_to', css_class='form-group col-md-4 mb-0'),\n                css_class='form-row'\n            ),\n            FormActions(\n                Submit('filter', 'Apply Filters', css_class='btn-primary'),\n                HTML('<a href=\"{% url \"lead_generation:lead_list\" %}\" class=\"btn btn-outline-secondary\">Clear</a>')\n            )\n        )\n\n\nclass BulkLeadActionForm(forms.Form):\n    \"\"\"Form for performing bulk actions on leads\"\"\"\n    \n    ACTION_CHOICES = [\n        ('assign_salesperson', 'Assign Salesperson'),\n        ('update_priority', 'Update Priority'),\n        ('update_status', 'Update Status'),\n        ('delete', 'Delete Leads'),\n    ]\n    \n    action = forms.ChoiceField(choices=ACTION_CHOICES)\n    \n    # Optional fields based on action\n    salesperson = forms.ModelChoiceField(\n        queryset=User.objects.filter(role='salesperson', is_active=True),\n        required=False\n    )\n    priority = forms.ChoiceField(choices=Lead.PRIORITY_CHOICES, required=False)\n    status = forms.ChoiceField(choices=Lead.STATUS_CHOICES, required=False)\n    \n    def __init__(self, *args, **kwargs):\n        user = kwargs.pop('user', None)\n        super().__init__(*args, **kwargs)\n        \n        # Filter salesperson choices based on user permissions\n        if user and user.role in ['supervisor', 'asm', 'avp']:\n            team_members = User.objects.filter(\n                team_membership__group__in=user.supervised_groups.all(),\n                role='salesperson'\n            )\n            self.fields['salesperson'].queryset = team_members\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h5><i class=\"fas fa-tasks\"></i> Bulk Actions</h5>'),\n            'action',\n            'salesperson',\n            Row(\n                Column('priority', css_class='form-group col-md-6 mb-0'),\n                Column('status', css_class='form-group col-md-6 mb-0'),\n                css_class='form-row'\n            ),\n            FormActions(\n                Submit('submit', 'Apply Action', css_class='btn-warning'),\n                HTML('<button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>')\n            )\n        )\n\n\nclass LeadImportForm(forms.Form):\n    \"\"\"Form for importing leads from CSV\"\"\"\n    \n    csv_file = forms.FileField(\n        help_text=\"Upload a CSV file with lead data. Required columns: first_name, last_name, email\"\n    )\n    default_source = forms.ModelChoiceField(\n        queryset=LeadSource.objects.filter(is_active=True),\n        help_text=\"Default source for imported leads if not specified in CSV\"\n    )\n    auto_assign = forms.BooleanField(\n        required=False,\n        help_text=\"Automatically assign leads to salespeople based on territory\"\n    )\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h4><i class=\"fas fa-file-upload\"></i> Import Leads from CSV</h4>'),\n            HTML('<div class=\"alert alert-info\"><strong>CSV Format:</strong><br>'\n                 'Required: first_name, last_name, email<br>'\n                 'Optional: phone_number, company_name, job_title, industry, territory, initial_interest</div>'),\n            'csv_file',\n            'default_source',\n            HTML('<div class=\"form-check mt-3\">'),\n            Field('auto_assign', css_class='form-check-input'),\n            HTML('</div>'),\n            FormActions(\n                Submit('submit', 'Import Leads', css_class='btn-success'),\n                HTML('<a href=\"{% url \"lead_generation:lead_list\" %}\" class=\"btn btn-secondary\">Cancel</a>')\n            )\n        )\n\n\nclass LeadNurturingCampaignForm(forms.ModelForm):\n    \"\"\"Form for creating lead nurturing campaigns\"\"\"\n    \n    class Meta:\n        model = LeadNurturingCampaign\n        fields = [\n            'name', 'description', 'target_status', 'target_score_min', 'target_score_max',\n            'email_template', 'follow_up_days', 'auto_assign_salesperson', 'is_active'\n        ]\n        widgets = {\n            'description': forms.Textarea(attrs={'rows': 3}),\n            'email_template': forms.Textarea(attrs={'rows': 8}),\n            'target_score_min': forms.NumberInput(attrs={'min': '0', 'max': '100'}),\n            'target_score_max': forms.NumberInput(attrs={'min': '0', 'max': '100'}),\n            'follow_up_days': forms.NumberInput(attrs={'min': '1'}),\n        }\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h4><i class=\"fas fa-envelope-open-text\"></i> Lead Nurturing Campaign</h4>'),\n            'name',\n            'description',\n            HTML('<hr><h5>Campaign Targeting</h5>'),\n            Row(\n                Column('target_status', css_class='form-group col-md-4 mb-0'),\n                Column('target_score_min', css_class='form-group col-md-4 mb-0'),\n                Column('target_score_max', css_class='form-group col-md-4 mb-0'),\n                css_class='form-row'\n            ),\n            HTML('<hr><h5>Campaign Content & Settings</h5>'),\n            'email_template',\n            Row(\n                Column('follow_up_days', css_class='form-group col-md-4 mb-0'),\n                Column('auto_assign_salesperson', css_class='form-group col-md-4 mb-0'),\n                Column('is_active', css_class='form-group col-md-4 mb-0'),\n                css_class='form-row'\n            ),\n            FormActions(\n                Submit('submit', 'Save Campaign', css_class='btn-primary'),\n                HTML('<a href=\"{% url \"lead_generation:campaign_list\" %}\" class=\"btn btn-secondary\">Cancel</a>')\n            )\n        )\n\n\nclass LeadAssignmentForm(forms.Form):\n    \"\"\"Form for assigning leads to salespeople\"\"\"\n    \n    salesperson = forms.ModelChoiceField(\n        queryset=User.objects.filter(role='salesperson', is_active=True),\n        help_text=\"Select salesperson to assign this lead to\"\n    )\n    \n    send_notification = forms.BooleanField(\n        required=False,\n        initial=True,\n        help_text=\"Send email notification to the assigned salesperson\"\n    )\n    \n    assignment_notes = forms.CharField(\n        widget=forms.Textarea(attrs={'rows': 3}),\n        required=False,\n        help_text=\"Optional notes for the assigned salesperson\"\n    )\n    \n    def __init__(self, *args, **kwargs):\n        user = kwargs.pop('user', None)\n        super().__init__(*args, **kwargs)\n        \n        # Filter salesperson choices based on user permissions\n        if user and user.role in ['supervisor', 'asm', 'avp']:\n            team_members = User.objects.filter(\n                team_membership__group__in=user.supervised_groups.all(),\n                role='salesperson'\n            )\n            self.fields['salesperson'].queryset = team_members\n        \n        self.helper = FormHelper()\n        self.helper.layout = Layout(\n            HTML('<h5><i class=\"fas fa-user-check\"></i> Assign Lead</h5>'),\n            'salesperson',\n            HTML('<div class=\"form-check mt-3\">'),\n            Field('send_notification', css_class='form-check-input'),\n            HTML('</div>'),\n            'assignment_notes',\n            FormActions(\n                Submit('submit', 'Assign Lead', css_class='btn-success'),\n                HTML('<button type=\"button\" class=\"btn btn-secondary\" data-bs-dismiss=\"modal\">Cancel</button>')\n            )\n        )


class LeadSearchForm(forms.Form):\n    \"\"\"Advanced search form for leads\"\"\"\n    \n    search_query = forms.CharField(\n        required=False,\n        widget=forms.TextInput(attrs={\n            'placeholder': 'Search by name, company, email, or phone...',\n            'class': 'form-control'\n        })\n    )\n    \n    def __init__(self, *args, **kwargs):\n        super().__init__(*args, **kwargs)\n        \n        self.helper = FormHelper()\n        self.helper.form_method = 'get'\n        self.helper.layout = Layout(\n            Row(\n                Column('search_query', css_class='form-group col-md-10 mb-0'),\n                Column(Submit('search', 'Search', css_class='btn-primary mt-2'), css_class='form-group col-md-2 mb-0'),\n                css_class='form-row align-items-end'\n            )\n        )
