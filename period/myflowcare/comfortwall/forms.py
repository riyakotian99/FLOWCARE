# comfortwall/forms.py
from django import forms
from .models import Post, Report

class PostForm(forms.ModelForm):
    consent = forms.BooleanField(label="I agree to the community guidelines")
    class Meta:
        model = Post
        fields = ['content', 'mood']
        widgets = {
            'content': forms.Textarea(attrs={'rows':4, 'placeholder':'Write what you feel...'}),
        }

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        fields = ['reason']
        widgets = {'reason': forms.Textarea(attrs={'rows':3, 'placeholder':'Why are you reporting this?'})}
