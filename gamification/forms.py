from django import forms
from .models import Mission

class MissionForm(forms.ModelForm):
    class Meta:
        model = Mission
        fields = ['title','description','mission_type','target_action','target_count','reward_points','is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class':'form-control','placeholder':'e.g., Create 5 Leads'}),
            'description': forms.Textarea(attrs={'class':'form-control','rows':3}),
            'mission_type': forms.Select(attrs={'class':'form-select'}),
            'target_action': forms.TextInput(attrs={'class':'form-control','placeholder':'e.g., create_lead'}),
            'target_count': forms.NumberInput(attrs={'class':'form-control','min':'1'}),
            'reward_points': forms.NumberInput(attrs={'class':'form-control','min':'0'}),
            'is_active': forms.CheckboxInput(attrs={'class':'form-check-input'}),
        }
