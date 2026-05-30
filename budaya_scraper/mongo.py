from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient

from .config import Settings


class MongoRepository:
    def __init__(self, settings: Settings) -> None:
        self.client = MongoClient(settings.mongo_uri)
        self.db = self.client[settings.mongo_db]
        self.list_collection = self.db[settings.mongo_list_collection]
        self.detail_collection = self.db[settings.mongo_detail_collection]
        self.list_collection.create_index("detail_url", unique=True)
        self.list_collection.create_index("slug")
        self.detail_collection.create_index("url", unique=True)
        self.detail_collection.create_index("entry_id")

    def upsert_list_item(self, item: dict[str, Any]) -> None:
        payload = dict(item)
        payload["updated_at"] = datetime.now(timezone.utc)
        self.list_collection.update_one(
            {"detail_url": payload["detail_url"]},
            {"$set": payload, "$setOnInsert": {"created_at": payload["updated_at"]}},
            upsert=True,
        )

    def upsert_detail_item(self, item: dict[str, Any]) -> None:
        payload = dict(item)
        payload["updated_at"] = datetime.now(timezone.utc)
        self.detail_collection.update_one(
            {"url": payload["url"]},
            {"$set": payload, "$setOnInsert": {"created_at": payload["updated_at"]}},
            upsert=True,
        )
        self.list_collection.update_one(
            {"detail_url": payload["url"]},
            {
                "$set": {
                    "detail_scraped": True,
                    "detail_scraped_at": payload["updated_at"],
                    "detail_entry_id": payload.get("entry_id"),
                    "detail_title": payload.get("title"),
                }
            },
        )

    def get_scraped_list_pages(self) -> set[int]:
        pages: set[int] = set()
        cursor = self.list_collection.find(
            {"source_page_url": {"$type": "string"}},
            {"source_page_url": 1, "_id": 0},
        )
        for document in cursor:
            source_page_url = document.get("source_page_url")
            if not source_page_url:
                continue
            match = re.search(r"[?&]page=(\d+)", source_page_url)
            if match:
                pages.add(int(match.group(1)))
        return pages
