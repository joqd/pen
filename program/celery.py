import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'program.settings')

app = Celery('program')

# Read all CELERY_* keys from Django settings (namespace='CELERY' means you
# write CELERY_BROKER_URL instead of just BROKER_URL in settings.py).
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks.py in every installed app (apps/orders/tasks.py etc.).
app.autodiscover_tasks()
