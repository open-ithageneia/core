# ruff: noqa: F403, F405
"""
Settings for running the production Docker image locally (no TLS).
Inherits everything from settings_production, then disables SSL/HSTS settings
that cause timeouts when there is no HTTPS reverse proxy.
"""
from .settings_production import *

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

USE_HTTPS_IN_ABSOLUTE_URLS = False

