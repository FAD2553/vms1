"""
Configuration WSGI pour le projet gestions_entree_sortie.

Il expose le callable WSGI en tant que variable de niveau module nommée « application ».

Pour plus d'informations sur ce fichier, voir
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestions_entree_sortie.settings')

application = get_wsgi_application()
