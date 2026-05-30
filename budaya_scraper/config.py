from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


DEFAULT_LIST_URL_TEMPLATE = (
    "https://budaya-indonesia.org/cari?gambar=0&audio=0&video=0&pdf=0&page={page}"
)


@dataclass(slots=True)
class Settings:
    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "budaya_indonesia")
    mongo_list_collection: str = os.getenv("MONGO_LIST_COLLECTION", "list_items")
    mongo_detail_collection: str = os.getenv("MONGO_DETAIL_COLLECTION", "detail_items")
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
    rabbitmq_queue: str = os.getenv("RABBITMQ_QUEUE", "budaya_indonesia.detail")
    user_agent: str = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (compatible; budaya-indonesia-scraper/1.0; +https://budaya-indonesia.org)",
    )
    connect_timeout: float = float(os.getenv("CONNECT_TIMEOUT", "15"))
    read_timeout: float = float(os.getenv("READ_TIMEOUT", "120"))
    gateway_timeout_sleep_seconds: float = float(os.getenv("GATEWAY_TIMEOUT_SLEEP_SECONDS", "180"))
    list_url_template: str = os.getenv("LIST_URL_TEMPLATE", DEFAULT_LIST_URL_TEMPLATE)

    @property
    def timeout(self) -> tuple[float, float]:
        return (self.connect_timeout, self.read_timeout)
