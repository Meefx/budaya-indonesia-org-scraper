# Scraper budaya-indonesia.org

Scraper ini dibagi menjadi dua alur:

1. `list`: ambil halaman hasil pencarian dengan `requests.get`, parse kartu item, simpan ke MongoDB, lalu publish `detail_url` ke RabbitMQ.
2. `detail-worker`: consume queue RabbitMQ, ambil halaman detail, parse field sedetail mungkin, lalu simpan ke MongoDB.

## Dependency

```bash
python -m pip install -r requirements.txt
```

File `.env` sekarang otomatis dibaca saat scraper dijalankan.

## Menjalankan RabbitMQ dengan Docker Compose

```bash
docker compose up -d
```

Endpoint default:

- AMQP: `amqp://guest:guest@localhost:5672/%2F`
- Management UI: `http://localhost:15672`

Credential default:

- Username: `guest`
- Password: `guest`

## Environment

Copy dulu file contoh env:

```bash
copy .env.example .env
```

Isi `.env.example`:

```dotenv
MONGO_URI=mongodb://localhost:27017
MONGO_DB=budaya_indonesia
MONGO_LIST_COLLECTION=list_items
MONGO_DETAIL_COLLECTION=detail_items
RABBITMQ_URL=amqp://guest:guest@localhost:5672/%2F
RABBITMQ_QUEUE=budaya_indonesia.detail
USER_AGENT=Mozilla/5.0 (compatible; budaya-indonesia-scraper/1.0; +https://budaya-indonesia.org)
LIST_URL_TEMPLATE=https://budaya-indonesia.org/cari?gambar=0&audio=0&video=0&pdf=0&page={page}
CONNECT_TIMEOUT=15
READ_TIMEOUT=120
GATEWAY_TIMEOUT_SLEEP_SECONDS=180
```

Timeout default sudah dinaikkan supaya lebih toleran terhadap server yang lambat: koneksi `15s`, read `120s`.
Kalau situs mengembalikan `HTTP 504`, scraper akan sleep selama `180` detik lalu retry URL yang sama.

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
