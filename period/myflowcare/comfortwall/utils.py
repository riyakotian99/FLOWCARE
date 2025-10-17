# comfortwall/utils.py
import hashlib
from django.conf import settings

def get_client_ip(request):
    """Extract client IP address safely."""
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')

def hash_ip(ip: str) -> str:
    """Hash IP for anonymity (never store raw IPs)."""
    if not ip:
        return ""
    return hashlib.sha256((ip + settings.SECRET_KEY).encode()).hexdigest()

def generate_delete_token(session_key: str) -> str:
    """Generate a unique delete token per session for self-deletion of posts."""
    return hashlib.sha256((session_key + settings.SECRET_KEY).encode()).hexdigest()[:32]

def generate_anon_name(session_key: str) -> str:
    """Generate a pseudonym like Comforter-1a2b for consistent anonymous identity."""
    if not session_key:
        return "Anonymous"
    short = hashlib.sha1(session_key.encode()).hexdigest()[:4]
    return f"Comforter-{short}"
