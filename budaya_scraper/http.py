from __future__ import annotations

import logging
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
        LOGGER.info("GET %s", url)
        response = self.session.get(url, timeout=self.settings.timeout)
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding or "utf-8"
        return response.text
