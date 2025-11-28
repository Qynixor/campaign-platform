import sys
import os
from django.core.management import call_command
from django.conf import settings

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'buskx.settings')
import django
django.setup()

with open('datadump.json', 'w', encoding='utf-8') as f:
    sys.stdout = f  # Redirect stdout to the file
    call_command(
        'dumpdata',
        exclude=['contenttypes', 'auth.permission'],
        indent=2
    )