# Scraper budaya-indonesia.org

Scraper ini dibagi menjadi dua alur:

1. `list`: ambil halaman hasil pencarian dengan `requests.get`, parse kartu item, simpan ke MongoDB, lalu publish `detail_url` ke RabbitMQ.
2. `detail-worker`: consume queue RabbitMQ, ambil halaman detail, parse field sedetail mungkin, lalu simpan ke MongoDB.

## Dependency

```bash
python -m pip install -r requirements.txt
```

## Environment

```bash
set MONGO_URI=mongodb://localhost:27017
set MONGO_DB=budaya_indonesia
set MONGO_LIST_COLLECTION=list_items
set MONGO_DETAIL_COLLECTION=detail_items
set RABBITMQ_URL=amqp://guest:guest@localhost:5672/%2F
set RABBITMQ_QUEUE=budaya_indonesia.detail
set CONNECT_TIMEOUT=15
set READ_TIMEOUT=120
```

Timeout default sudah dinaikkan supaya lebih toleran terhadap server yang lambat: koneksi `15s`, read `120s`.

## Menjalankan scraper list

```bash
python -m budaya_scraper list --start-page 1 --end-page 10
```

Kalau hanya ingin simpan ke MongoDB tanpa publish ke RabbitMQ:

```bash
python -m budaya_scraper list --start-page 1 --end-page 10 --no-publish
```

## Menjalankan scraper detail manual

```bash
python -m budaya_scraper detail --url https://budaya-indonesia.org/Busana-Dramatari-Arja
python -m budaya_scraper detail --url-file detail-item/ex2/url.txt
```

## Menjalankan worker detail dari RabbitMQ

```bash
python -m budaya_scraper detail-worker
```

## Field yang diparse

List item:

- `title`
- `detail_url`
- `slug`
- `image_url`
- `element`
- `element_icon_url`
- `province`
- `summary`
- `source_page_url`

Detail item:

- `entry_id`
- `title`
- `meta_title`
- `breadcrumbs`
- `element`
- `provinces`
- `badges`
- `author`
- `description_html`
- `description_text`
- `images`
- `pdfs`
- `videos`
- `audios`
- `source_links`
- `related_entries`
- `attachment_counts`

## Test parser dari sampel HTML lokal

```bash
python -m unittest discover -s tests -v
```
