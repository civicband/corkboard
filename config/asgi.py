"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

import djp
import logfire
import sentry_sdk
from django.conf import settings
from django.core.asgi import get_asgi_application
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def get_release():
    """Read release SHA from file baked into Docker image at build time."""
    try:
        with open("/.release") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "development"


# Initialize Sentry if DSN is configured
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=os.environ.get("SENTRY_ENVIRONMENT", "production"),
        release=get_release(),
        send_default_pii=True,
        max_request_body_size="always",
        traces_sample_rate=0.1,
    )

# Get the ASGI application first (this initializes Django)
application = djp.asgi_wrapper(get_asgi_application())

# Configure Logfire after Django is initialized
if settings.DEBUG:
    # Development: console output only, no data sent to Logfire
    logfire.configure(send_to_logfire=False)
else:
    # Production: full telemetry if token is configured
    logfire_token = os.environ.get("LOGFIRE_TOKEN")
    if logfire_token:
        from logfire import SamplingOptions

        logfire.configure(
            token=logfire_token,
            service_name="corkboard",
            # Keep all errors/warnings and slow traces (>5s), sample 5% of normal traffic
            sampling=SamplingOptions.level_or_duration(
                level_threshold="warning",
                duration_threshold=5.0,
                background_rate=0.05,
            ),
        )
        logfire.instrument_django()
        logfire.instrument_httpx()
        logfire.instrument_sqlite3()
        # Propagate trace context to thread pools (used by Datasette for queries)
        from opentelemetry.instrumentation.threading import ThreadingInstrumentor

        ThreadingInstrumentor().instrument()

# Wrap with Sentry middleware for error capture
if sentry_dsn:
    application = SentryAsgiMiddleware(application)
