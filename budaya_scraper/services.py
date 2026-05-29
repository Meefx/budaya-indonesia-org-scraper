from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Iterable

from .config import Settings
from .http import HttpClient
from .mongo import MongoRepository
from .parsers import parse_detail_page, parse_list_page
from .rabbitmq import RabbitQueue


LOGGER = logging.getLogger(__name__)


class ListScraperService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = HttpClient(settings)
        self.mongo = MongoRepository(settings)
        self.queue = RabbitQueue(settings)

    def scrape_pages(self, pages: Iterable[int], publish_messages: bool = True) -> None:
        for page in pages:
            page_url = self.settings.list_url_template.format(page=page)
            html = self.http.get_text(page_url)
            parsed = parse_list_page(html, page_url)
            LOGGER.info(
                "Parsed page=%s total_items=%s total_pages=%s",
                parsed["current_page"],
                len(parsed["items"]),
                parsed["total_pages"],
            )
            for item in parsed["items"]:
                item["scraped_at"] = datetime.now(timezone.utc)
                self.mongo.upsert_list_item(item)
                if publish_messages:
                    self.queue.publish(
                        {
                            "detail_url": item["detail_url"],
                            "slug": item.get("slug"),
                            "source_page_url": item.get("source_page_url"),
                            "published_at": item["scraped_at"].isoformat(),
                        }
                    )


class DetailScraperService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.http = HttpClient(settings)
        self.mongo = MongoRepository(settings)
        self.queue = RabbitQueue(settings)

    def scrape_detail_url(self, detail_url: str) -> dict:
        html = self.http.get_text(detail_url)
        parsed = parse_detail_page(html, detail_url)
        parsed["scraped_at"] = datetime.now(timezone.utc)
        self.mongo.upsert_detail_item(parsed)
        return parsed

    def run_worker(self) -> None:
        LOGGER.info("Consuming queue=%s", self.settings.rabbitmq_queue)

        def _handler(message: dict) -> None:
            detail_url = message.get("detail_url")
            if not detail_url:
                raise ValueError("detail_url not found in queue message")
            LOGGER.info("Scraping detail %s", detail_url)
            self.scrape_detail_url(detail_url)

        self.queue.consume(_handler)
