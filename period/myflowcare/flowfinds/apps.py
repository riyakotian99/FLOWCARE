from django.apps import AppConfig
from mongoengine import connect
from django.conf import settings

class FlowfindsConfig(AppConfig):
    name = "flowfinds"
    verbose_name = "FlowFinds"

    def ready(self):
        # Connect to MongoDB when the app is loaded
        try:
            connect(host=getattr(settings, "MONGO_URI", "mongodb://localhost:27017/flowfinds_db"))
        except Exception:
            # ignore connection noise during some manage.py commands
            pass
