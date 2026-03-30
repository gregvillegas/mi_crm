from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from teams.models import Group
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, HTML, Fieldset

class SalespersonCreationForm(UserCreationForm):
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, help_text="The group this salesperson will belong to.")
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('first_name', 'last_name', 'email', 'mobile_number', 'initials', 'group',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Fieldset(
                'Account Information',
                Row(
                    Column('username', css_class='form-group col-md-12 mb-3'),
                ),
                Row(
                    Column('password1', css_class='form-group col-md-6 mb-3'),
                    Column('password2', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            Fieldset(
                'Personal Information',
                Row(
                    Column('first_name', css_class='form-group col-md-6 mb-3'),
                    Column('last_name', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('email', css_class='form-group col-md-6 mb-3'),
                    Column('mobile_number', css_class='form-group col-md-6 mb-3'),
                ),
                Row(
                    Column('initials', css_class='form-group col-md-6 mb-3'),
                    Column('group', css_class='form-group col-md-6 mb-3'),
                ),
            ),
            HTML('<br>'),
            Submit('submit', 'Create Salesperson', css_class='btn btn-primary')
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = 'salesperson'
        if commit:
            user.save()
            # TeamMembership is created after user is saved
            from teams.models import TeamMembership
            TeamMembership.objects.create(user=user, group=self.cleaned_data['group'])
        return user

class UserProfileForm(forms.ModelForm):
    """Form for users to update their own profile"""
    class Meta:
        model = User
        fields = ['profile_picture', 'signature_image', 'first_name', 'last_name', 'email', 'mobile_number', 'initials', 'job_title']
        help_texts = {
            'initials': 'Your initials (e.g., JD)',
            'mobile_number': 'Your contact number',
            'profile_picture': 'Upload a profile picture (optional)'
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.layout = Layout(
            Row(
                Column('profile_picture', css_class='form-group col-md-12 mb-3'),
            ),
            Row(
                Column('signature_image', css_class='form-group col-md-12 mb-3'),
            ),
            Row(
                Column('first_name', css_class='form-group col-md-6 mb-3'),
                Column('last_name', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('email', css_class='form-group col-md-6 mb-3'),
                Column('mobile_number', css_class='form-group col-md-6 mb-3'),
            ),
            Row(
                Column('initials', css_class='form-group col-md-6 mb-3'),
                Column('job_title', css_class='form-group col-md-6 mb-3'),
            ),
            HTML('<br>'),
            Submit('submit', 'Update Profile', css_class='btn btn-primary')
        )
