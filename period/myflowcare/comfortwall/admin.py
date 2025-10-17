# comfortwall/admin.py
from django.contrib import admin
from .models import Post, Report

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('anon_name','created_at','is_approved','is_flagged','reports_count')
    list_filter = ('is_approved','is_flagged','created_at')
    search_fields = ('content',)

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('post', 'reason', 'other_text', 'created_at', 'reporter_ip_hash')
    search_fields = ('reason', 'other_text')
