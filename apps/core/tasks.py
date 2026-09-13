import logging
from datetime import timedelta

import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

from .models import ExchangeRate

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
)
def update_usd_exchange_rate(self):
    logger.info('Fetching USD exchange rate from netarz.ir')

    try:
        response = requests.get(
            'https://netarz.ir/api/fx/v1/rates/USD',
            headers={
                'Authorization': f'Bearer {settings.NETARZ_TOKEN}',
            },
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        # autoretry_for handles the retry, but we log the reason first
        logger.warning('Failed to fetch USD rate (attempt %s): %s', self.request.retries + 1, exc)
        raise
    except ValueError as exc:
        logger.error('Invalid JSON response from netarz.ir: %s', exc)
        return

    try:
        rate = payload['data']['mid']
    except (KeyError, TypeError) as exc:
        logger.error('Unexpected payload structure from netarz.ir: %s | payload=%s', exc, payload)
        return

    latest = ExchangeRate.objects.filter(currency='USD').order_by('-fetched_at').first()
    if latest and latest.rate == rate:
        logger.info('USD rate unchanged (%s); skipping insert', rate)
        return

    exchange_rate = ExchangeRate.objects.create(
        currency='USD',
        rate=rate,
        source='netarz.ir',
        fetched_at=timezone.now(),
    )
    logger.info(
        'Stored new USD exchange rate: id=%s rate=%s (previous=%s)',
        exchange_rate.id,
        rate,
        latest.rate if latest else None,
    )


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_old_exchange_rates(self):
    """
    Delete exchange rate records older than 30 days, per currency,
    while always keeping at least the most recent record for each
    currency — even if it happens to be older than the cutoff.

    This guards against the edge case where a currency's rate hasn't
    changed in over a month (so no new rows were inserted) and a naive
    delete would wipe out every row, leaving the app with no rate to
    read at all.
    """
    cutoff = timezone.now() - timedelta(days=30)

    try:
        currencies = list(ExchangeRate.objects.values_list('currency', flat=True).distinct())
    except Exception as exc:
        logger.exception('Failed to fetch currency list for cleanup: %s', exc)
        raise self.retry(exc=exc)

    total_deleted = 0

    for currency in currencies:
        try:
            latest_id = (
                ExchangeRate.objects.filter(currency=currency)
                .order_by('-fetched_at')
                .values_list('id', flat=True)
                .first()
            )

            if latest_id is None:
                # Nothing to clean up for this currency.
                continue

            deleted_count, _ = (
                ExchangeRate.objects.filter(currency=currency, fetched_at__lt=cutoff).exclude(id=latest_id).delete()
            )

            total_deleted += deleted_count

            if deleted_count:
                logger.info(
                    "Deleted %s old '%s' exchange rate record(s) (kept latest id=%s)",
                    deleted_count,
                    currency,
                    latest_id,
                )
            else:
                logger.info(
                    "No old '%s' exchange rate records to delete (latest kept id=%s)",
                    currency,
                    latest_id,
                )
        except Exception as exc:
            # Don't let one currency's failure abort cleanup for the rest.
            logger.exception("Error cleaning up exchange rates for '%s': %s", currency, exc)
            continue

    logger.info('Exchange rate cleanup finished; total deleted=%s', total_deleted)
    return total_deleted
