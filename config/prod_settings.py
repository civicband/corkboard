from config.settings import *

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "civic.db",
    },
    "sites": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR.parent / "civic-band" / "sites.db",
    },
}
