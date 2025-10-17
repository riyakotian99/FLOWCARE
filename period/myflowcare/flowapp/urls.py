from django.urls import path
from . import views   

app_name = "flowapp"  

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('home/', views.home, name='home'),
    path('aboutus/', views.aboutus, name='aboutus'),
    path('comfortwall/', views.comfortwall, name='comfortwall'),
    path('helpmap/', views.helpmap, name='helpmap'),
    path('flowfacts/', views.flowfacts, name='flowfacts'),
    path('flowfinds/', views.flowfinds, name='flowfinds'),
    path('firstperiodguide/', views.firstperiodguide, name='firstperiodguide'),
    path('articles/', views.articles, name='articles'),
    path('infographics/', views.infographics, name='infographics'),
    path('homeremedies/', views.homeremedies, name='homeremedies'),
    path('diet/', views.diet, name='diet'),
    path('care/', views.care, name='care'),
    path("add-cycle/", views.add_cycle, name="add_cycle"),
    path("cyclemate/", views.cyclemate, name="cyclemate"),
    path("logs/add/", views.add_daily_log, name="add_daily_log"),
    path("logs/", views.list_daily_logs, name="list_daily_logs"),
    path("insights/", views.insights, name="insights"),
    path("reminders/schedule/", views.schedule_period_reminders_view, name="schedule_reminders"),
    path("gynecologists/", views.gynecologists, name="gynecologists"),
    path('ai-chat/', views.ai_chat_page, name='ai_chat_page'),
    path('api/ai_chat/', views.api_ai_chat, name='api_ai_chat'),
    path("gynecologists/", views.gynecologists, name="gynecologists"),
    path("gynecologists/book/<slug:slug>/", views.book_appointment, name="book"),
    path("ngo/", views.ngo, name="ngo"),
    path("ngo/join/<slug:slug>/<str:kind>/", views.join_volunteer, name="ngo_join"),
    path('videos-podcasts/', views.videos_podcasts, name='videos_podcasts'), 
    path("privacy-policy/", views.privacy_policy, name="privacy_policy"),
    path("terms-of-service/", views.terms_of_service, name="terms_of_service"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    
]