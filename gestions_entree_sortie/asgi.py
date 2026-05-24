"""
Configuration ASGI pour le projet gestions_entree_sortie.

Il expose le callable ASGI en tant que variable de niveau module nommée « application ».

Pour plus d'informations sur ce fichier, voir
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestions_entree_sortie.settings')

application = get_asgi_application()
