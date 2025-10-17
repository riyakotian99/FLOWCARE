from django import forms
from datetime import date
from .models import Appointment
from .models import VolunteerSignup
MOOD_CHOICES = [
    ("happy", "Happy"), ("okay", "Okay"), ("irritable", "Irritable"),
    ("sad", "Sad"), ("tired", "Tired"), ("anxious", "Anxious"),
]

FLOW_CHOICES = [
    ("none", "None"), ("light", "Light"), ("medium", "Medium"), ("heavy", "Heavy"),
]

SYMPTOM_CHOICES = [
    ("cramps", "Cramps"), ("bloating", "Bloating"), ("fatigue", "Fatigue"),
    ("headache", "Headache"), ("backache", "Backache"), ("acne", "Acne"),
    ("nausea", "Nausea"), ("food_cravings", "Food cravings"), ("mood_swings", "Mood swings"),
]

class DailyLogForm(forms.Form):
    log_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date", "max": date.today().isoformat()}),
        initial=date.today,
    )
    mood = forms.ChoiceField(choices=MOOD_CHOICES, required=False)
    flow = forms.ChoiceField(choices=FLOW_CHOICES, required=False)
    symptoms = forms.MultipleChoiceField(
        choices=SYMPTOM_CHOICES, required=False,
        widget=forms.CheckboxSelectMultiple
    )
    notes = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False)

###############################---book appointment---###########################
# flowapp/forms.py
class AppointmentForm(forms.ModelForm):
    preferred_date = forms.DateField(widget=forms.DateInput(attrs={"type":"date"}), required=False)
    preferred_time = forms.TimeField(widget=forms.TimeInput(attrs={"type":"time"}), required=False)

    class Meta:
        model = Appointment
        fields = ['patient_name', 'phone', 'email', 'preferred_date', 'preferred_time', 'notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows':3}),
        }

##############-----NGO------################
class VolunteerSignupForm(forms.ModelForm):
    class Meta:
        model = VolunteerSignup
        fields = ['name','phone','email','availability','notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows':3}),
            'availability': forms.TextInput(attrs={'placeholder':'e.g. Weekends, Evenings'}),
        }