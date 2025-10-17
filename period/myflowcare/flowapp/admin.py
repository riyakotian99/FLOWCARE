# flowapp/admin.py
from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from .mongo_period_tracker import PeriodTrackerRepository
from datetime import timezone
from .models import Appointment
from .models import VolunteerSignup
repo = PeriodTrackerRepository(mongo_uri="mongodb://localhost:27017", db_name="flowcare")

@staff_member_required
def mongo_users_view(request):
    # fetch users (limit)
    raw_users = list(repo.users.find().sort("last_seen", -1).limit(200))

    users = []
    for u in raw_users:
        uid = u.get("user_id")
        last_seen = u.get("last_seen")
        last_seen_iso = (last_seen.astimezone(timezone.utc).isoformat() if last_seen else None)

        # fetch last 5 cycles for this user (most recent first)
        cycles_cursor = repo.cycles.find({"user_id": uid}).sort("start_date", -1).limit(5)
        cycles = []
        for c in cycles_cursor:
            cycles.append({
                "start_date": (c.get("start_date").astimezone(timezone.utc).date().isoformat() if c.get("start_date") else None),
                "end_date": (c.get("end_date").astimezone(timezone.utc).date().isoformat() if c.get("end_date") else None),
                "period_length_days": c.get("period_length_days"),
                "cycle_length_days": c.get("cycle_length_days"),
            })

        # fetch last 5 daily logs for this user
        logs_cursor = repo.daily_logs.find({"user_id": uid}).sort("log_date", -1).limit(5)
        logs = []
        for l in logs_cursor:
            logs.append({
                "log_date": (l.get("log_date").astimezone(timezone.utc).date().isoformat() if l.get("log_date") else None),
                "mood": l.get("mood"),
                "flow": l.get("flow"),
                "symptoms": l.get("symptoms") or [],
                "notes": l.get("notes"),
            })

        users.append({
            "user_id": uid,
            "last_seen": last_seen_iso,
            "other_fields": [(k, v) for k, v in u.items() if k not in ("_id", "user_id", "last_seen")],
            "cycles": cycles,
            "logs": logs,
        })

    return render(request, "admin/mongo_users.html", {"users": users})

def get_admin_urls(urls):
    def wrapped():
        my_urls = [
            path("mongo-users/", admin.site.admin_view(mongo_users_view), name="mongo-users"),
        ]
        return my_urls + urls()
    return wrapped

admin.site.get_urls = get_admin_urls(admin.site.get_urls)

# flowapp/admin.py
#book-appointment
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_name','doctor_name','phone','preferred_date','status','created_at')
    list_filter = ('status','doctor_name')
    search_fields = ('patient_name','phone','email','doctor_name')

###-------NGO-------####
@admin.register(VolunteerSignup)
class VolunteerSignupAdmin(admin.ModelAdmin):
    list_display = ('name','display_name','kind','phone','status','created_at')
    list_filter = ('kind','status')
    search_fields = ('name','phone','email','display_name')