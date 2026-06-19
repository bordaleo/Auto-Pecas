"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

_default_module = 'config.production' if os.getenv('RENDER') else 'config.settings'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', _default_module)

application = get_wsgi_application()
