# helpmap/views.py
from django.shortcuts import render

def helpmap_view(request):
    return render(request, "helpmap/helpmap.html")
