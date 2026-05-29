from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .config import Settings
from .services import DetailScraperService, ListScraperService


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    if not verbose:
        logging.getLogger("pika").setLevel(logging.WARNING)
        logging.getLogger("pymongo").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scraper budaya-indonesia.org")
    parser.add_argument("--verbose", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="Scrape halaman list lalu simpan dan publish ke RabbitMQ")
    list_parser.add_argument("--start-page", type=int, required=True)
    list_parser.add_argument("--end-page", type=int)
    list_parser.add_argument("--no-publish", action="store_true")

    detail_parser = subparsers.add_parser("detail", help="Scrape satu atau banyak URL detail")
    detail_parser.add_argument("--url")
    detail_parser.add_argument("--url-file", type=Path)

    subparsers.add_parser("detail-worker", help="Consume RabbitMQ lalu scrape detail")
    return parser


def _read_urls(path: Path) -> list[str]:
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    configure_logging(args.verbose)
    settings = Settings()

    if args.command == "list":
        end_page = args.end_page or args.start_page
        pages = range(args.start_page, end_page + 1)
        ListScraperService(settings).scrape_pages(pages, publish_messages=not args.no_publish)
        return 0

    if args.command == "detail":
        service = DetailScraperService(settings)
        urls: list[str] = []
        if args.url:
            urls.append(args.url)
        if args.url_file:
            urls.extend(_read_urls(args.url_file))
        if not urls:
            parser.error("detail membutuhkan --url atau --url-file")
        for url in urls:
            service.scrape_detail_url(url)
        return 0

    if args.command == "detail-worker":
        DetailScraperService(settings).run_worker()
        return 0

    parser.error("Unknown command")
    return 2
