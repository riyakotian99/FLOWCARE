# comfortwall/urls.py
from django.urls import path
from . import views

app_name = "comfortwall"

urlpatterns = [
    path("", views.list_posts, name="list"),
    path("create/", views.create_post, name="create"),
    path("delete/<uuid:post_id>/", views.delete_post, name="delete"),
    path("like/<uuid:post_id>/", views.like_post, name="like"),
    path("report/", views.report_post, name="report"),   # <--- important
    path("moderation/", views.moderation_queue, name="moderation"),
]
