from __future__ import annotations

import unittest
from pathlib import Path

from budaya_scraper.parsers import parse_detail_page, parse_list_page


ROOT = Path(__file__).resolve().parents[1]


class ParserTests(unittest.TestCase):
    def test_parse_list_page(self) -> None:
        html = (ROOT / "list-item" / "index.html").read_text(encoding="utf-8")
        page_url = (ROOT / "list-item" / "url.txt").read_text(encoding="utf-8").strip()

        parsed = parse_list_page(html, page_url)

        self.assertEqual(parsed["current_page"], 6519)
        self.assertEqual(parsed["total_pages"], 6519)
        self.assertEqual(parsed["total_entries"], 58670)
        self.assertGreaterEqual(len(parsed["items"]), 8)
        self.assertEqual(parsed["items"][0]["title"], "Songket Palembang: Jejak Sriwijaya dalam Selembar Kain Martabat")
        self.assertEqual(parsed["items"][0]["element"], "Motif Kain")
        self.assertEqual(parsed["items"][0]["province"], "Sumatera Selatan")

    def test_parse_detail_page_with_pdf(self) -> None:
        html = (ROOT / "detail-item" / "ex2" / "index.html").read_text(encoding="utf-8")
        page_url = (ROOT / "detail-item" / "ex2" / "url.txt").read_text(encoding="utf-8").strip()

        parsed = parse_detail_page(html, page_url)

        self.assertEqual(parsed["entry_id"], "6448")
        self.assertEqual(parsed["title"], "Busana Dramatari Arja")
        self.assertEqual(parsed["element"], "Pakaian Tradisional")
        self.assertIn("Bali", parsed["provinces"])
        self.assertEqual(parsed["author"]["name"], "hallowulandari")
        self.assertEqual(len(parsed["images"]), 1)
        self.assertEqual(len(parsed["pdfs"]), 1)
        self.assertEqual(parsed["attachment_counts"]["videos"], 0)

    def test_parse_detail_page_with_video(self) -> None:
        html = (ROOT / "detail-item" / "ex1" / "index.html").read_text(encoding="utf-8")
        page_url = (ROOT / "detail-item" / "ex1" / "url.txt").read_text(encoding="utf-8").strip()

        parsed = parse_detail_page(html, page_url)

        self.assertEqual(parsed["entry_id"], "1778")
        self.assertEqual(parsed["title"], "Senam Tari Musik Sasambo")
        self.assertEqual(parsed["attachment_counts"]["images"], 3)
        self.assertEqual(parsed["attachment_counts"]["videos"], 1)
        self.assertEqual(len(parsed["videos"]), 1)


if __name__ == "__main__":
    unittest.main()
