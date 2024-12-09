from django import forms
from .models import BatchJob

class BatchJobForm(forms.ModelForm):
    class Meta:
        model = BatchJob
        fields = ['command', 'timing', 'start_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }