from django.urls import path
from . import views

app_name = "helpmap"

urlpatterns = [
    path("", views.helpmap_view, name="helpmap"),
]
