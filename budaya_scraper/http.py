from __future__ import annotations

import logging
import time
from typing import Optional

import requests

from .config import Settings


LOGGER = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, settings: Settings, session: Optional[requests.Session] = None) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": settings.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
            }
        )

    def get_text(self, url: str) -> str:
        attempt = 1
        while True:
            LOGGER.info("GET %s", url)
            response = self.session.get(url, timeout=self.settings.timeout)
            try:
                response.raise_for_status()
            except requests.HTTPError:
                if response.status_code == 504:
                    sleep_seconds = self.settings.gateway_timeout_sleep_seconds
                    LOGGER.warning(
                        "HTTP 504 untuk %s pada attempt=%s. Sleep %.0f detik lalu retry.",
                        url,
                        attempt,
                        sleep_seconds,
                    )
                    attempt += 1
                    time.sleep(sleep_seconds)
                    continue
                raise
            response.encoding = response.encoding or response.apparent_encoding or "utf-8"
            return response.text
