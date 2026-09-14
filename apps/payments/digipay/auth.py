import base64
import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings
from django.core.cache import cache

from .exceptions import DigipayAuthenticationError

logger = logging.getLogger(__name__)


class DigipayAuthClient:
    """Handles Digipay OAuth token retrieval, refresh and caching.

    Required settings: DIGIPAY_CLIENT_ID, DIGIPAY_CLIENT_SECRET,
    DIGIPAY_USERNAME, DIGIPAY_PASSWORD. Base URL switches on settings.DEBUG.
    """

    CACHE_KEY_ACCESS_TOKEN = 'digipay:access_token'
    CACHE_KEY_REFRESH_TOKEN = 'digipay:refresh_token'
    TOKEN_ENDPOINT = '/oauth/token'

    def __init__(self):
        self.base_url = self._get_base_url()
        self.client_id = settings.DIGIPAY_CLIENT_ID
        self.client_secret = settings.DIGIPAY_CLIENT_SECRET
        self.username = settings.DIGIPAY_USERNAME
        self.password = settings.DIGIPAY_PASSWORD
        self.timeout = getattr(settings, 'DIGIPAY_TIMEOUT', 15)

    @staticmethod
    def _get_base_url() -> str:
        if settings.DEBUG:
            return 'https://uat.mydigipay.info/digipay/api'
        return 'https://api.mydigipay.com/digipay/api'

    def _basic_auth_header(self) -> str:
        raw = f'{self.client_id}:{self.client_secret}'.encode('utf-8')
        return f'Basic {base64.b64encode(raw).decode("utf-8")}'

    def _fetch_new_token(self) -> Dict[str, Any]:
        url = f'{self.base_url}{self.TOKEN_ENDPOINT}'
        headers = {'Authorization': self._basic_auth_header()}
        data = {'username': self.username, 'password': self.password, 'grant_type': 'password'}

        try:
            response = requests.post(url, headers=headers, data=data, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.exception('Digipay token request failed')
            raise DigipayAuthenticationError(f'Digipay connection error: {exc}') from exc

        if response.status_code != 200:
            logger.error('Digipay authentication failed: %s - %s', response.status_code, response.text)
            raise DigipayAuthenticationError(
                f'Digipay authentication failed (status={response.status_code})',
                status_code=response.status_code,
                response_data=self._safe_json(response),
            )

        token_data = response.json()
        self._cache_tokens(token_data)
        return token_data

    def _refresh_access_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        url = f'{self.base_url}{self.TOKEN_ENDPOINT}'
        headers = {'Authorization': self._basic_auth_header()}
        data = {'grant_type': 'refresh_token', 'refresh_token': refresh_token}

        try:
            response = requests.post(url, headers=headers, data=data, timeout=self.timeout)
        except requests.RequestException:
            logger.exception('Digipay refresh token request failed')
            return None

        if response.status_code != 200:
            logger.warning('Digipay refresh token failed: %s - %s', response.status_code, response.text)
            return None

        token_data = response.json()
        self._cache_tokens(token_data)
        return token_data

    def _cache_tokens(self, token_data: Dict[str, Any]) -> None:
        expires_in = token_data.get('expires_in', 3599)
        safety_margin = 30
        cache.set(
            self.CACHE_KEY_ACCESS_TOKEN,
            token_data['access_token'],
            timeout=max(expires_in - safety_margin, 10),
        )
        refresh_token = token_data.get('refresh_token')
        if refresh_token:
            cache.set(self.CACHE_KEY_REFRESH_TOKEN, refresh_token, timeout=None)

    def get_access_token(self, force_refresh: bool = False) -> str:
        if not force_refresh:
            token = cache.get(self.CACHE_KEY_ACCESS_TOKEN)
            if token:
                return token

        refresh_token = cache.get(self.CACHE_KEY_REFRESH_TOKEN)
        if refresh_token:
            token_data = self._refresh_access_token(refresh_token)
            if token_data:
                return token_data['access_token']

        token_data = self._fetch_new_token()
        return token_data['access_token']

    @staticmethod
    def _safe_json(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {'raw': response.text}
