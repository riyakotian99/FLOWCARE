
from django.contrib import admin
from django.urls import path,include
from flowapp import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path("helpmap/", include("helpmap.urls", namespace="helpmap")),
    path('comfortwall/', include('comfortwall.urls', namespace='comfortwall')),
    path('flowfinds/', include('flowfinds.urls', namespace='flowfinds')),
    path("", include(("flowapp.urls", "flowapp"), namespace="flowapp")),
    
]
# serve media in development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


