import logging
from typing import Any, Dict, Optional

import requests
from django.conf import settings

from .auth import DigipayAuthClient
from .exceptions import DigipayAPIError

logger = logging.getLogger(__name__)


class BaseDigipayService:
    """Shared HTTP layer for all Digipay services: headers, auth, retry on 401."""

    DIGIPAY_VERSION = '2022-02-02'
    AGENT = 'WEB'

    def __init__(self, gateway=None, auth_client: Optional[DigipayAuthClient] = None):
        if auth_client is None:
            if gateway is None:
                raise ValueError('BaseDigipayService requires either "gateway" or "auth_client".')
            auth_client = DigipayAuthClient(gateway)
        self.auth_client = auth_client
        self.base_url = self.auth_client.base_url
        self.timeout = getattr(settings, 'DIGIPAY_TIMEOUT', 15)

    def _headers(self) -> Dict[str, str]:
        return {
            'Agent': self.AGENT,
            'Digipay-Version': self.DIGIPAY_VERSION,
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.auth_client.get_access_token()}',
        }

    def request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry_on_auth_error: bool = True,
    ) -> Dict[str, Any]:
        url = f'{self.base_url}{path}'
        headers = self._headers()

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.exception('Digipay API request failed: %s %s', method, url)
            raise DigipayAPIError(f'Digipay connection error: {exc}') from exc

        if response.status_code == 401 and retry_on_auth_error:
            self.auth_client.get_access_token(force_refresh=True)
            return self.request(method, path, params, json_data, retry_on_auth_error=False)

        if not response.ok:
            logger.error('Digipay API error: %s %s -> %s - %s', method, url, response.status_code, response.text)
            raise DigipayAPIError(
                f'Digipay API error (status={response.status_code})',
                status_code=response.status_code,
                response_data=self._safe_json(response),
            )

        return self._safe_json(response)

    @staticmethod
    def _safe_json(response: requests.Response) -> Dict[str, Any]:
        try:
            return response.json()
        except ValueError:
            return {'raw': response.text}
