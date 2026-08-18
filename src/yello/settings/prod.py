"""Production settings — import base then tighten for deployment."""

from yello.settings.base import *  # noqa: F401,F403

DEBUG = False
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
X_FRAME_OPTIONS = "DENY"
