import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gestion_emprunts.settings')
django.setup()

from core.models import LogAction

actions = LogAction.objects.values_list('action', flat=True).distinct()
for a in actions:
    print(f"|{a}| - Hex: {' '.join(hex(ord(c)) for c in a)}")

# Count occurrences of CONSULTATION_CNIB variants
from django.db.models import Count
variants = LogAction.objects.values('action').annotate(count=Count('id')).filter(action__icontains='CONSULTATION_CNIB')
for v in variants:
    print(f"'{v['action']}' : {v['count']}")
