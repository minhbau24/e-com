"""WSGI config for search_project."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "search_project.settings")

application = get_wsgi_application()
