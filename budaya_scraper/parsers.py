from __future__ import annotations

import re
from html import unescape
from typing import Any
from urllib.parse import parse_qs, urljoin, urlparse

from bs4 import BeautifulSoup, Tag


PROVINCES = {
    "Aceh",
    "Bali",
    "Banten",
    "Bengkulu",
    "DKI Jakarta",
    "Daerah Istimewa Yogyakarta",
    "Gorontalo",
    "Jambi",
    "Jawa Barat",
    "Jawa Tengah",
    "Jawa Timur",
    "Kalimantan Barat",
    "Kalimantan Selatan",
    "Kalimantan Tengah",
    "Kalimantan Timur",
    "Kalimantan Utara",
    "Kepulauan Bangka Belitung",
    "Kepulauan Riau",
    "Lampung",
    "Maluku",
    "Maluku Utara",
    "Nusa Tenggara Barat",
    "Nusa Tenggara Timur",
    "Papua",
    "Papua Barat",
    "Papua Barat Daya",
    "Papua Pegunungan",
    "Papua Selatan",
    "Papua Tengah",
    "Riau",
    "Sulawesi Barat",
    "Sulawesi Selatan",
    "Sulawesi Tengah",
    "Sulawesi Tenggara",
    "Sulawesi Utara",
    "Sumatera Barat",
    "Sumatera Selatan",
    "Sumatera Utara",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_lines(value: str) -> str:
    lines = [normalize_space(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def absolute_url(url: str, base_url: str) -> str:
    return urljoin(base_url, url)


def extract_slug(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return path.split("/")[-1] if path else ""


def _first_text(tag: Tag | None) -> str | None:
    if not tag:
        return None
    value = normalize_space(tag.get_text(" ", strip=True))
    return value or None


def _extract_total_entries(soup: BeautifulSoup) -> int | None:
    text = soup.get_text("\n", strip=True)
    match = re.search(r"([\d\.]+)\s+entri ditemukan", text, re.IGNORECASE)
    if not match:
        return None
    return int(match.group(1).replace(".", ""))


def _extract_current_page(page_url: str, soup: BeautifulSoup) -> int | None:
    active = soup.select_one("li.page-item a.page-link.active")
    if active:
        text = normalize_space(active.get_text())
        if text.isdigit():
            return int(text)
    query = parse_qs(urlparse(page_url).query)
    page = query.get("page", [None])[0]
    return int(page) if page and page.isdigit() else None


def _extract_total_pages(soup: BeautifulSoup) -> int | None:
    pages: list[int] = []
    for link in soup.select("li.page-item a.page-link"):
        text = normalize_space(link.get_text())
        if text.isdigit():
            pages.append(int(text))
    return max(pages) if pages else None


def parse_list_page(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select(".card-entry.custom-card")
    items: list[dict[str, Any]] = []

    for card in cards:
        title_link = card.select_one("h6 a[href]")
        title = _first_text(title_link)
        detail_url = absolute_url(title_link["href"], page_url) if title_link and title_link.get("href") else None
        if not title or not detail_url:
            continue

        image = card.select_one("img.entry-thumbnail")
        badge_icon = card.select_one("div.rounded-pill img")
        badge_label = card.select_one("div.rounded-pill span")
        province_candidates = [
            normalize_space(span.get_text())
            for span in card.select("div.rounded-pill span")
            if normalize_space(span.get_text()) in PROVINCES
        ]
        summary_tag = card.select_one("p")
        summary_text = clean_lines(summary_tag.get_text("\n", strip=True)) if summary_tag else None

        items.append(
            {
                "title": title,
                "detail_url": detail_url,
                "slug": extract_slug(detail_url),
                "image_url": absolute_url(image["src"], page_url) if image and image.get("src") else None,
                "element": _first_text(badge_label),
                "element_icon_url": absolute_url(badge_icon["src"], page_url)
                if badge_icon and badge_icon.get("src")
                else None,
                "province": province_candidates[0] if province_candidates else None,
                "summary": summary_text,
                "source_page_url": page_url,
            }
        )

    return {
        "source_page_url": page_url,
        "current_page": _extract_current_page(page_url, soup),
        "total_pages": _extract_total_pages(soup),
        "total_entries": _extract_total_entries(soup),
        "items": items,
    }


def _extract_badges(card_body: Tag) -> list[dict[str, Any]]:
    badges: list[dict[str, Any]] = []
    for badge in card_body.select("span.badge"):
        text = _first_text(badge)
        if not text:
            continue
        img = badge.select_one("img")
        badges.append(
            {
                "label": text,
                "icon_url": img.get("src") if img else None,
                "kind": "province" if text in PROVINCES else "tag",
            }
        )
    return badges


def _extract_author(card_body: Tag, base_url: str) -> dict[str, Any] | None:
    author_block = card_body.select_one("div.d-flex.align-items-center.gap-2.text-muted")
    if not author_block:
        return None
    avatar = author_block.select_one("img")
    profile_link = author_block.select_one("a[href]")
    date_text = None
    for div in author_block.select("div"):
        text = _first_text(div)
        if text and text.startswith("-"):
            date_text = text.lstrip("-").strip()
            break
    return {
        "name": _first_text(profile_link),
        "profile_url": absolute_url(profile_link["href"], base_url) if profile_link and profile_link.get("href") else None,
        "avatar_url": absolute_url(avatar["src"], base_url) if avatar and avatar.get("src") else None,
        "published_at_raw": date_text,
    }


def _extract_description(card_body: Tag) -> tuple[str | None, str | None]:
    content = card_body.select_one("div.p-2")
    if not content:
        return None, None
    html = content.decode_contents().strip() or None
    text = clean_lines(content.get_text("\n", strip=True)) or None
    return html, text


def _extract_images(card_body: Tag, base_url: str) -> list[dict[str, Any]]:
    images: list[dict[str, Any]] = []
    for item in card_body.select("#carouselControl .carousel-item"):
        img = item.select_one("img[src]")
        link = item.select_one("a[href]")
        if not img:
            continue
        images.append(
            {
                "src": absolute_url(img["src"], base_url),
                "full_url": absolute_url(link["href"], base_url) if link and link.get("href") else absolute_url(img["src"], base_url),
                "alt": img.get("alt"),
                "file_edit_url": absolute_url(img["data-edit-url"], base_url) if img.get("data-edit-url") else None,
                "file_detail_url": absolute_url(img["data-detail-url"], base_url) if img.get("data-detail-url") else None,
            }
        )
    return images


def _extract_pdfs(card_body: Tag, base_url: str) -> list[dict[str, Any]]:
    pdfs: list[dict[str, Any]] = []
    for card in card_body.select(".card-pdf"):
        canvas = card.select_one("canvas[data-getpdf-url]")
        action_links = card.select("a.file-action-link[href]")
        pdf_url = card.get("data-pdf")
        pdfs.append(
            {
                "url": absolute_url(pdf_url, base_url) if pdf_url else None,
                "preview_url": absolute_url(canvas["data-getpdf-url"], base_url) if canvas and canvas.get("data-getpdf-url") else None,
                "file_edit_url": absolute_url(action_links[0]["href"], base_url) if len(action_links) > 0 else None,
                "file_detail_url": absolute_url(action_links[1]["href"], base_url) if len(action_links) > 1 else None,
            }
        )
    return pdfs


def _extract_media(card_body: Tag, selector: str, attr_name: str, base_url: str) -> list[str]:
    urls: list[str] = []
    for tag in card_body.select(selector):
        value = tag.get(attr_name)
        if value:
            urls.append(absolute_url(value, base_url))
    return list(dict.fromkeys(urls))


def _extract_breadcrumbs(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    breadcrumbs: list[dict[str, Any]] = []
    for li in soup.select("nav[aria-label='breadcrumb'] li.breadcrumb-item"):
        link = li.select_one("a[href]")
        breadcrumbs.append(
            {
                "label": _first_text(li),
                "url": absolute_url(link["href"], base_url) if link and link.get("href") else None,
            }
        )
    return breadcrumbs


def _extract_related_entries(soup: BeautifulSoup, base_url: str) -> list[dict[str, Any]]:
    related: list[dict[str, Any]] = []
    for card in soup.select(".col-lg-4 .card-entry.custom-card"):
        link = card.select_one("h6 a[href]")
        if not link:
            continue
        image = card.select_one("img.entry-thumbnail")
        related.append(
            {
                "title": _first_text(link),
                "url": absolute_url(link["href"], base_url),
                "slug": extract_slug(link["href"]),
                "image_url": absolute_url(image["src"], base_url) if image and image.get("src") else None,
            }
        )
    return related


def parse_detail_page(html: str, page_url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")
    meta_entry = soup.select_one("meta[name='entry-id']")
    main_column = soup.select_one(".col-12.col-lg-8 .card.custom-card .card-body")
    if not main_column:
        raise ValueError("Main detail container not found")

    title_tag = main_column.select_one("h5")
    title = _first_text(title_tag) or _first_text(soup.title)
    badges = _extract_badges(main_column)
    author = _extract_author(main_column, page_url)
    description_html, description_text = _extract_description(main_column)
    images = _extract_images(main_column, page_url)
    pdfs = _extract_pdfs(main_column, page_url)
    videos = _extract_media(main_column, "video source[src], video[src]", "src", page_url)
    audios = _extract_media(main_column, "audio source[src], audio[src]", "src", page_url)
    source_links = [absolute_url(a["href"], page_url) for a in main_column.select("div.p-2 a[href]")]
    source_links = list(dict.fromkeys(source_links))

    province_labels = [badge["label"] for badge in badges if badge["label"] in PROVINCES]
    element_badge = badges[0]["label"] if badges else None
    meta_description = soup.select_one("meta[name='description']")

    return {
        "entry_id": meta_entry.get("content") if meta_entry else None,
        "url": page_url,
        "slug": extract_slug(page_url),
        "title": unescape(title) if title else None,
        "meta_title": _first_text(soup.title),
        "meta_description": meta_description.get("content") if meta_description else None,
        "breadcrumbs": _extract_breadcrumbs(soup, page_url),
        "element": element_badge,
        "provinces": province_labels,
        "badges": badges,
        "author": author,
        "description_html": description_html,
        "description_text": description_text,
        "images": images,
        "pdfs": pdfs,
        "videos": videos,
        "audios": audios,
        "source_links": source_links,
        "related_entries": _extract_related_entries(soup, page_url),
        "attachment_counts": {
            "images": len(images),
            "pdfs": len([pdf for pdf in pdfs if pdf.get("url")]),
            "videos": len(videos),
            "audios": len(audios),
        },
    }
