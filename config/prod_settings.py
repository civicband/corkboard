from config.settings import *

DEBUG = False

# DATABASES is already configured in config.settings with DATABASE_URL support
# Don't override it here - let the base settings handle Postgres vs SQLite fallback

# Trust proxy headers for HTTPS detection
# This ensures redirect URIs use https:// instead of http://
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
