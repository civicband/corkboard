"""
ASGI config for config project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

import djp
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# sentry_sdk.init(
#     "https://11ecb14e4a3249129b039b57090320c1@andromeda.nebulosa-moth.ts.net/3",

#     send_default_pii=True,
#     max_request_body_size="always",
#     sample_rate=0.25,
#     traces_sample_rate=0,
# )

application = djp.asgi_wrapper(get_asgi_application())

# application = SentryAsgiMiddleware(application)
