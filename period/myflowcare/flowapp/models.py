# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class MyUser(models.Model):
    username = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.username

#book appointment
# flowapp/models.py
class Appointment(models.Model):
    doctor_slug = models.SlugField(max_length=100)
    doctor_name = models.CharField(max_length=200)
    patient_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    preferred_date = models.DateField(blank=True, null=True)
    preferred_time = models.TimeField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Accepted")  # predefined accepted
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient_name} → {self.doctor_name} ({self.status})"

#####----NGO----#####
class VolunteerSignup(models.Model):
    # kind: person | group | solo
    kind = models.CharField(max_length=10)
    slug = models.SlugField(max_length=120)
    display_name = models.CharField(max_length=200)   # doctor/group/solo label
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    availability = models.CharField(max_length=200, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, default="Accepted")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} -> {self.display_name} ({self.kind})"