from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ExchangeRate


@shared_task
def update_usd_exchange_rate():
    response = requests.get(
        'https://netarz.ir/api/fx/v1/rates/USD',
        headers={
            'Authorization': f'Bearer {settings.NETARZ_TOKEN}',
        },
        timeout=10,
    )
    response.raise_for_status()

    payload = response.json()
    rate = payload['data']['mid']

    latest = ExchangeRate.objects.filter(currency='USD').first()
    if latest and latest.rate == rate:
        return

    ExchangeRate.objects.create(
        currency='USD',
        rate=rate,
        source='netarz.ir',
        fetched_at=timezone.now(),
    )


@shared_task
def delete_old_exchange_rates():
    cutoff = timezone.now() - timedelta(days=30)
    ExchangeRate.objects.filter(fetched_at__lt=cutoff).delete()
