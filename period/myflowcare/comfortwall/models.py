# comfortwall/models.py
import uuid
import hashlib
from django.conf import settings
from django.db import models
from django.utils import timezone

# Mood options for posts
MOOD_CHOICES = [
    ("neutral", "Neutral"),
    ("happy", "Happy"),
    ("sad", "Sad"),
    ("anxious", "Anxious"),
    ("angry", "Angry"),
]

def hash_ip(ip: str) -> str:
    """Store hashed IP for abuse-handling (do NOT store raw IP)."""
    if not ip:
        return ""
    # Consider using a separate salt in settings (e.g. settings.IP_HASH_SALT) for extra safety
    return hashlib.sha256((ip + settings.SECRET_KEY).encode()).hexdigest()


class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    content = models.TextField()
    mood = models.CharField(max_length=20, choices=MOOD_CHOICES, blank=True)
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")

    # anonymity & light ownership
    anon_name = models.CharField(max_length=30, default="Anonymous")
    session_key = models.CharField(max_length=100, blank=True)
    ip_hash = models.CharField(max_length=64, blank=True)

    # moderation
    is_approved = models.BooleanField(default=False)  # default: moderation queue
    is_flagged = models.BooleanField(default=False)
    reports_count = models.PositiveIntegerField(default=0)

    # NEW: likes counter
    likes_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)

    delete_token = models.CharField(
        max_length=64,
        blank=True,
        help_text="Token stored in user's session to allow self-delete"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_approved", "created_at"]),
        ]

    def __str__(self):
        return f"{self.anon_name[:15]} — {self.created_at:%Y-%m-%d %H:%M}"


class Report(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="reports")
    reason = models.TextField(blank=True)
    other_text = models.TextField(blank=True)   # ✅ NEW FIELD
    reporter_ip_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Report for {self.post.id} at {self.created_at:%Y-%m-%d %H:%M}"
