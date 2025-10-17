import json
import re
import logging
import requests
from django.shortcuts import render, redirect
from django.views import View # type: ignore
from django.http import HttpResponse # type: ignore
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from datetime import datetime, date,timezone
from .mongo_period_tracker import PeriodTrackerRepository, to_utc_datetime
from .forms import DailyLogForm
from django.utils.timezone import now as tz_now
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import ensure_csrf_cookie  
from django.core.cache import cache 
####book appointment###
from django.urls import reverse
from .forms import AppointmentForm
from .models import Appointment
####NGO#######
from .forms import VolunteerSignupForm
from .models import VolunteerSignup
# Create your views here.
#image
def flowcare(request):
    return render(request,'flowcare.html')
#page inheritance
def login(request):
    return render(request,'login.html')
def register(request):
    return render(request, 'register.html')
def home(request):
    return render(request,'home.html')
def aboutus(request):
    return render(request, 'aboutus.html')
def comfortwall(request):
    return render(request,'comfortwall.html')
def helpmap(request):
    return render(request,'helpmap.html')
def flowfacts(request):
    return render(request,'flowfacts.html')
def flowfinds(request):
    return render(request,'flowfinds.html')
def firstperiodguide(request):
    return render(request, 'firstperiodguide.html')
def articles(request):
    return render(request, 'articles.html')
def infographics(request):
    return render(request,'infographics.html')
def homeremedies(request):
    return render(request,'homeremedies.html')
def diet(request):
    return render(request,'diet.html')
def care(request):
    return render(request,'care.html')
def gynecologists(request):
    return render(request, 'gynecologists.html')
def ngo(request):
    return render(request, 'ngo.html')
def videos_podcasts(request):
    return render(request, 'videos_podcasts.html')
def privacy_policy(request):
    return render(request, "privacy_policy.html")
def terms_of_service(request):
    return render(request, "terms_of_service.html")
def disclaimer(request):
    return render(request, "disclaimer.html")
# Register Page
def register(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']

        # Check if passwords match
        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect('flowapp:register')

        # Strong password check
        password_pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$'
        if not re.match(password_pattern, password1):
            messages.error(request, 
                "Password must be at least 8 characters long, include 1 uppercase, "
                "1 lowercase, 1 number, and 1 special character (@$!%*?&).")
            return redirect('flowapp:register')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect('flowapp:register')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already used")
            return redirect('flowapp:register')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created successfully! You can now login.")
        return redirect('flowapp:login')

    return render(request, 'register.html')



# Login Page
def login_view(request):
    if request.method == 'POST':
        login_input = request.POST['login_input']   # can be username OR email
        password = request.POST['password']

        # Check if login_input is an email
        if '@' in login_input:
            try:
                user_obj = User.objects.get(email=login_input)
                username = user_obj.username
            except User.DoesNotExist:
                messages.error(request, "No account found with this email")
                return redirect('flowapp:login')
        else:
            username = login_input  # treat input as username

        # Authenticate user
        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            # <-- ADDED success message here
            messages.success(request, f"Welcome {user.username}, you have successfully logged in to FlowCare!")
            return redirect('flowapp:home')
        else:
            messages.error(request, "Invalid username/email or password")
            return redirect('flowapp:login')

    return render(request, 'login.html')
#logout part
def logout_view(request):
    """
    Log the user out. Uses POST to avoid CSRF-related logout attacks.
    After logout, redirect to the login page (or home) with a success message.
    """
    if request.method == "POST":
        # Optionally capture user info before logging out
        username = request.user.username if request.user.is_authenticated else None

        # perform logout
        auth_logout(request)

        # show on-site message
        if username:
            messages.success(request, f"Goodbye {username}! You have been logged out of FlowCare.")
        else:
            messages.success(request, "You have been logged out.")

        return redirect('flowapp:login')

    # If someone tries GET, you can either redirect or show a confirmation page.
    # Simple redirect to home/login:
    return redirect('flowapp:home')

#------------------------------------------#period tracker-----------------------------------------------------------------------------------
# Initialize repository with your MongoDB URI
from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

# import your form(s)
from .forms import DailyLogForm

# import the repository (make sure path matches your project)
from .mongo_period_tracker import PeriodTrackerRepository

# initialize repo (same as you had)
repo = PeriodTrackerRepository(mongo_uri="mongodb://localhost:27017", db_name="flowcare")


@login_required
def add_cycle(request):
    if request.method == "POST":
        start_str = request.POST.get("start_date")
        end_str = request.POST.get("end_date")
        start = datetime.strptime(start_str, "%Y-%m-%d").date()
        end = datetime.strptime(end_str, "%Y-%m-%d").date() if end_str else None
        user_id = str(request.user.id)  # store Django user id as string

        try:
            inserted = repo.add_cycle_entry(user_id=user_id, start=start, end=end)

            # --- UPSELL: ensure a users doc exists and store last_seen + latest_activity ---
            try:
                repo.users.update_one(
                    {"user_id": user_id},
                    {"$set": {
                        "last_seen": datetime.now(timezone.utc),
                        "latest_activity": {
                            "type": "cycle",
                            "timestamp": datetime.now(timezone.utc),
                            "ref_start": to_utc_datetime(start)
                        }
                    }},
                    upsert=True
                )
            except Exception:
                # non-fatal - ignore DB write errors for the user mirror
                pass

            # fetch previous and predicted info to show immediate feedback
            prev_and_pred = repo.get_prev_and_predicted(user_id=user_id)
            prev = prev_and_pred.get("previous_start")
            predicted = prev_and_pred.get("predicted_next_start")

            msg = "Cycle saved."
            if prev:
                msg += f" Previous start: {prev.isoformat()}."
            if predicted:
                msg += f" Predicted next start: {predicted.isoformat()}."
            messages.success(request, msg)
        except ValueError as e:
            messages.error(request, str(e))
        except Exception:
            messages.error(request, "Could not save cycle. Please try again.")

        return redirect("flowapp:cyclemate")

    return render(request, "flowapp/add_cycle.html")

@login_required
def cyclemate(request):
    user_id = str(request.user.id)

    # Prediction & ovulation (as dicts we can easily render in templates)
    prediction_obj = repo.predict_next_period(user_id)
    prediction = None
    if prediction_obj:
        prediction = {
            "predicted_start": prediction_obj.predicted_start.isoformat(),
            "predicted_end": prediction_obj.predicted_end.isoformat() if prediction_obj.predicted_end else None,
            "avg_cycle_length_days": prediction_obj.avg_cycle_length_days,
            "avg_period_length_days": prediction_obj.avg_period_length_days,
        }

    ovulation_obj = repo.predict_ovulation(user_id)
    ovulation = None
    if ovulation_obj:
        ovulation = {
            "ovulation_day": ovulation_obj.ovulation_day.isoformat(),
            "fertile_start": ovulation_obj.fertile_start.isoformat(),
            "fertile_end": ovulation_obj.fertile_end.isoformat(),
        }

    # top pre-period symptoms
    top_sym = repo.top_preperiod_symptoms(user_id, window_days=3, limit=5)

    # previous / latest / predicted quick info
    prev_and_pred = repo.get_prev_and_predicted(user_id=user_id)
    prev_ctx = {
        "previous_start": prev_and_pred.get("previous_start").isoformat() if prev_and_pred.get("previous_start") else None,
        "latest_start": prev_and_pred.get("latest_start").isoformat() if prev_and_pred.get("latest_start") else None,
        "predicted_next": prev_and_pred.get("predicted_next_start").isoformat() if prev_and_pred.get("predicted_next_start") else None,
    }

    return render(request, "flowapp/cyclemate.html", {
        "prediction": prediction,
        "ovulation": ovulation,
        "top_symptoms": top_sym,
        "prev_info": prev_ctx,
    })


@login_required
def add_daily_log(request):
    if request.method == "POST":
        form = DailyLogForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            user_id = str(request.user.id)
            try:
                repo.log_daily(
                    user_id=user_id,
                    log_dt=data["log_date"],
                    mood=data.get("mood") or None,
                    flow=data.get("flow") or None,
                    symptoms=data.get("symptoms") or [],
                    notes=data.get("notes") or None,
                )

                # --- UPSELL: ensure a users doc exists and store last_seen + latest_activity ---
                try:
                    repo.users.update_one(
                        {"user_id": user_id},
                        {"$set": {
                            "last_seen": datetime.now(timezone.utc),
                            "latest_activity": {
                                "type": "daily_log",
                                "timestamp": datetime.now(timezone.utc),
                                "ref_date": to_utc_datetime(data["log_date"])
                            }
                        }},
                        upsert=True
                    )
                except Exception:
                    pass

                messages.success(request, "Daily log saved.")
            except Exception:
                messages.error(request, "Could not save daily log. Please try again.")
            return redirect("flowapp:list_daily_logs")
    else:
        form = DailyLogForm()
    return render(request, "flowapp/daily_log_form.html", {"form": form})


@login_required
def list_daily_logs(request):
    user_id = str(request.user.id)
    # Pull last 30 logs (newest first)
    logs = list(
        repo.daily_logs.find({"user_id": user_id})
        .sort("log_date", -1).limit(30)
    )
    # convert datetimes to date strings for template
    parsed = []
    for d in logs:
        parsed.append({
            "date": d["log_date"].date().isoformat(),
            "mood": d.get("mood"),
            "flow": d.get("flow"),
            "symptoms": ", ".join(d.get("symptoms") or []),
            "notes": d.get("notes"),
        })
    return render(request, "flowapp/daily_log_list.html", {"logs": parsed})


@login_required
def insights(request):
    user_id = str(request.user.id)
    # top symptoms in the N days before actual starts
    top_sym = repo.top_preperiod_symptoms(user_id=user_id, window_days=3, limit=5)

    # prediction/ovulation (reusable dicts)
    prediction_obj = repo.predict_next_period(user_id)
    prediction = None
    if prediction_obj:
        prediction = {
            "predicted_start": prediction_obj.predicted_start.isoformat(),
            "predicted_end": prediction_obj.predicted_end.isoformat() if prediction_obj.predicted_end else None,
        }

    ovulation_obj = repo.predict_ovulation(user_id)
    ovulation = None
    if ovulation_obj:
        ovulation = {
            "ovulation_day": ovulation_obj.ovulation_day.isoformat(),
            "fertile_start": ovulation_obj.fertile_start.isoformat(),
            "fertile_end": ovulation_obj.fertile_end.isoformat(),
        }

    ctx = {
        "top_symptoms": top_sym,  # list[(symptom, count)]
        "prediction": prediction,
        "ovulation": ovulation,
    }
    return render(request, "flowapp/insights.html", ctx)


@login_required
def schedule_period_reminders_view(request):
    user_id = str(request.user.id)
    created = repo.schedule_period_reminders(user_id=user_id)
    messages.success(request, f"Scheduled {len(created)} reminders for your upcoming period.")
    return redirect("flowapp:insights")


#-------------------------------------------#myth-busting quiz--------------------------------------------------------------------------
# Put this in flowapp/views.py (replace any previous api_ai_chat)
logger = logging.getLogger(__name__)

# ---- helpers ----
def _get_client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")

RATE_LIMIT_PER_MIN = 60
def _rate_limited(ip: str) -> bool:
    if not ip:
        return False
    key = f"ai_rl:{ip}"
    count = cache.get(key, 0) + 1
    cache.set(key, count, timeout=60)
    return count > RATE_LIMIT_PER_MIN

# ---- page view ----
@ensure_csrf_cookie
def ai_chat_page(request):
    """
    Render the chat UI and set the CSRF cookie.
    Template: templates/ai_chat.html
    """
    return render(request, "ai_chat.html")


# ---- API view (Gemini) ----
@require_POST
def api_ai_chat(request):
    """
    POST JSON { "message": "..." } -> returns JSON { "reply": "..." }
    Uses Google Generative Language (Gemini). Ensure GEN_API_KEY in settings.
    """
    # parse JSON
    try:
        body = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    message = (body.get("message") or "").strip()
    if not message:
        return JsonResponse({"error": "message is required"}, status=400)

    # rate limit by IP
    ip = _get_client_ip(request)
    if _rate_limited(ip):
        return JsonResponse({"error": "Too many requests"}, status=429)

    API_KEY = getattr(settings, "GEN_API_KEY", None)
    MODEL = getattr(settings, "GEN_MODEL", "gemini-1.5-flash-latest")
    if not API_KEY:
        return JsonResponse({"error": "Server missing GEN_API_KEY in settings"}, status=500)

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "X-goog-api-key": API_KEY,
    }

    prompt = (
        "You are a helpful, concise assistant for FlowCare. Answer clearly and politely.\n\n"
        f"User: {message}\nAssistant:"
    )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=25)

        # DEV: if provider returns non-2xx, include status and a chunk of response for debugging
        if not resp.ok:
            logger.error("Gemini API error %s: %s", resp.status_code, resp.text[:1000])
            return JsonResponse({
                "error": "Gemini API request failed",
                "status_code": resp.status_code,
                "api_response": resp.text[:2000]
            }, status=502)

        result = resp.json()
        try:
            text_output = result['candidates'][0]['content']['parts'][0]['text']
        except Exception:
            logger.exception("Unexpected Gemini response structure: %s", result)
            return JsonResponse({"error": "Unexpected API response", "raw": result}, status=502)

        return JsonResponse({"reply": text_output})

    except requests.RequestException as e:
        logger.exception("Requests exception calling Gemini")
        return JsonResponse({"error": "External API request failed", "details": str(e)}, status=502)
    except Exception as e:
        logger.exception("Unexpected server error in api_ai_chat")
        return JsonResponse({"error": "Server error", "details": str(e)}, status=500)
    
#############----appointment------###
DOCTORS = {
    "asha-patil": {
        "name": "Dr. Asha Patil",
        "clinic": "Sunrise Women's Clinic — Mumbai",
        "phone": "+919876543210",
        "email": "asha@example.com",
    },
    "neha-kapoor": {
        "name": "Dr. Neha Kapoor",
        "clinic": "Bloom Gynae Centre — Delhi",
        "phone": "+919123456789",
        "email": "neha@example.com",
    },
    "ritu-sharma": {
        "name": "Dr. Ritu Sharma",
        "clinic": "Lotus Women’s Health — Bengaluru",
        "phone": "+919988776655",
        "email": "ritu@example.com",
    },
    "shalini-mehta": {
        "name": "Dr. Shalini Mehta",
        "clinic": "Harmony Women’s Clinic — Thane (West), Mumbai",
        "phone": "+919812345600",
        "email": "shalini@example.com",
    },
    "vibha-kulkarni": {
        "name": "Dr. Vibha Kulkarni",
        "clinic": "Wellness Gynae Care — Navi Mumbai (Vashi)",
        "phone": "+919800112233",
        "email": "vibha@example.com",
    },
    "anjali-deshmukh": {
        "name": "Dr. Anjali Deshmukh",
        "clinic": "CarePoint Women’s Hospital — Dombivli, Mumbai Metropolitan",
        "phone": "+919877654321",
        "email": "anjali@example.com",
    },
    "kavita-pawar": {
        "name": "Dr. Kavita Pawar",
        "clinic": "Shree Sai Maternity Clinic — Kalyan (East), Mumbai Region",
        "phone": "+919844556677",
        "email": "kavita@example.com",
    },
    "meera-pillai": {
        "name": "Dr. Meera Pillai",
        "clinic": "Lotus Bloom Clinic — Panvel, Navi Mumbai",
        "phone": "+919877009988",
        "email": "meera@example.com",
    },
}
def gynecologists(request):
    return render(request, 'gynecologists.html', {'doctors': DOCTORS})

def book_appointment(request, slug):
    doctor = DOCTORS.get(slug)
    if not doctor:
        return render(request, '404.html', status=404)

    # POST -> validate, save, then redirect to same page with ?accepted=1 (PRG)
    if request.method == "POST":
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appt = form.save(commit=False)
            appt.doctor_slug = slug
            appt.doctor_name = doctor['name']
            appt.status = "Accepted"   # predefined immediate acceptance
            appt.save()
            # PRG: redirect so the GET response can contain accepted flag
            return redirect(reverse('flowapp:book', kwargs={'slug': slug}) + '?accepted=1')
        # if form invalid, fall through to render template with form errors

    else:
        form = AppointmentForm()

    # Determine whether to show acceptance modal (from query param)
    accepted = request.GET.get('accepted') == '1'

    context = {
        'doctor': doctor,
        'form': form,
        'accepted': accepted,
        'doctor_slug': slug,
    }
    return render(request, 'book_appointment.html', context)

##################--------------------NGO------------------------###################
VOLUNTEERS = {
    "nisha-shah": {
        "name": "Nisha Shah",
        "role": "Period-education volunteer",
        "location": "Mumbai",
        "story": "I started volunteering after I realised young girls in local schools needed practical guidance on period hygiene.",
    },
    "ramya-iyer": {
        "name": "Ramya Iyer",
        "role": "Counselor & outreach",
        "location": "Navi Mumbai",
        "story": "I support girls with counselling and dignity-pack distribution.",
    },
    "sneha-patel": {
        "name": "Sneha Patel",
        "role": "Awareness campaigner",
        "location": "Thane",
        "story": "Organises awareness drives in colleges to reduce stigma around periods.",
    },
    "anu-kulkarni": {
        "name": "Anu Kulkarni",
        "role": "Community coordinator",
        "location": "Panvel",
        "story": "Helps coordinate sanitary pad distribution in housing societies.",
    },
    "meera-joshi": {
        "name": "Meera Joshi",
        "role": "Health educator",
        "location": "Kalyan",
        "story": "Conducts small group workshops on menstrual hygiene for teenagers.",
    },
    "lata-deshmukh": {
        "name": "Lata Deshmukh",
        "role": "NGO field worker",
        "location": "Dombivli",
        "story": "Works in slum areas to ensure women get access to affordable sanitary products.",
    },
    "pallavi-kapoor": {
        "name": "Pallavi Kapoor",
        "role": "Workshop volunteer",
        "location": "Vashi",
        "story": "Runs interactive sessions in schools and community halls about menstrual health.",
    },
}

GROUPS = {
    "mumbai-outreach": {
        "name": "Mumbai Outreach",
        "members": "12 active volunteers",
        "summary": "Community workshops, school sessions, and sanitary kit distribution across Mumbai suburbs.",
    },
    "panvel-womens-group": {
        "name": "Panvel Women’s Group",
        "members": "8 active volunteers",
        "summary": "Peer-support and local clinic partnership for low-cost checkups.",
    },
    "thane-support-network": {
        "name": "Thane Support Network",
        "members": "10 active volunteers",
        "summary": "Organises awareness campaigns and donation drives in Thane.",
    },
    "kalyan-youth-group": {
        "name": "Kalyan Youth Group",
        "members": "15 active volunteers",
        "summary": "Youth-led initiatives for menstrual education in colleges and schools.",
    },
    "navi-mumbai-helpers": {
        "name": "Navi Mumbai Helpers",
        "members": "20 active volunteers",
        "summary": "Coordinates pad distribution across Navi Mumbai and holds community events.",
    },
    "dombivli-care-team": {
        "name": "Dombivli Care Team",
        "members": "9 active volunteers",
        "summary": "Focused on counselling and spreading awareness about period health in local communities.",
    },
    "women-empower-club": {
        "name": "Women Empower Club",
        "members": "18 active volunteers",
        "summary": "Works with schools and NGOs to empower young women with correct health information.",
    },
}
# VOLUNTEERS and GROUPS dicts here

def ngo(request):
    # a short real/fictional story to show on the page
    story = {
    'title': "One girl's story — 'Asha's first period'",
    'text': """When Asha was 12, she got her first period while at school. Nobody had explained to her what was happening, and she felt scared and embarrassed. For a whole week, she stayed home, missing her classes because she didn’t know how to manage it.

That’s when a volunteer stepped in. She sat with Asha, explained what periods are, and gave her access to pads and basic guidance. With that support, Asha returned to school, feeling more confident and prepared.

Today, Asha continues her studies with pride — and her story shows how one volunteer can change a life."""
}

    return render(request, 'ngo.html', {
        'story': story,
        'volunteers': VOLUNTEERS,
        'groups': GROUPS,
    })

def join_volunteer(request, slug, kind):
    """
    kind in ('person', 'group', 'solo')
    slug: volunteer slug (for person/group) or 'solo' slug if kind=solo
    """
    # Resolve display label
    if kind == 'person':
        item = VOLUNTEERS.get(slug)
        display = item['name'] if item else slug
    elif kind == 'group':
        item = GROUPS.get(slug)
        display = item['name'] if item else slug
    else:
        item = None
        display = "Volunteer Alone"

    # PRG flow
    if request.method == 'POST':
        form = VolunteerSignupForm(request.POST)
        if form.is_valid():
            signup = form.save(commit=False)
            signup.kind = kind
            signup.slug = slug
            signup.display_name = display
            signup.status = "Accepted"   # predefined acceptance
            signup.save()
            return redirect(reverse('flowapp:ngo_join', kwargs={'slug': slug, 'kind': kind}) + '?accepted=1')
    else:
        form = VolunteerSignupForm()

    accepted = request.GET.get('accepted') == '1'
    return render(request, 'join_form.html', {
        'form': form,
        'kind': kind,
        'slug': slug,
        'display': display,
        'accepted': accepted,
    })
