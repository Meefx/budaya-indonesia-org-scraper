import os
import argparse
import mimetypes
import json
import requests
import boto3
import pika
from urllib.parse import urlparse, unquote
from pymongo import MongoClient
from pymongo.collection import Collection
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load env variables
load_dotenv()

# AWS S3 Settings
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# MongoDB Settings
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB = os.getenv("MONGO_DB", "budaya_indonesia")
MONGO_DETAIL_COLLECTION = os.getenv("MONGO_DETAIL_COLLECTION", "detail_items")

# RabbitMQ Settings
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/%2F")
MIGRATE_QUEUE_NAME = "budaya_indonesia.migrate_s3"

def get_s3_client():
    if not all([AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, S3_BUCKET_NAME]):
        raise ValueError("Please set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and S3_BUCKET_NAME in your .env file.")
    return boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

def get_mongo_collection():
    db_client = MongoClient(MONGO_URI)
    return db_client[MONGO_DB][MONGO_DETAIL_COLLECTION]

def get_rabbitmq_channel(connection):
    channel = connection.channel()
    channel.queue_declare(queue=MIGRATE_QUEUE_NAME, durable=True)
    return channel

def publish_tasks(limit=None):
    collection = get_mongo_collection()
    if limit:
        print(f"Fetching {limit} documents to publish to RabbitMQ (testing mode)...")
    else:
        print("Fetching documents to publish to RabbitMQ...")
    
    # Hanya cari file yang berpotensi memiliki attachment untuk menghemat antrian
    cursor = collection.find({
        "$or": [
            {"images.0": {"$exists": True}},
            {"audios.0": {"$exists": True}},
            {"videos.0": {"$exists": True}},
            {"pdfs.0": {"$exists": True}},
        ]
    }, {"_id": 1})
    
    if limit:
        cursor = cursor.limit(limit)
    
    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = get_rabbitmq_channel(connection)

    count = 0
    for doc in cursor:
        doc_id = str(doc["_id"])
        channel.basic_publish(
            exchange="",
            routing_key=MIGRATE_QUEUE_NAME,
            body=json.dumps({"doc_id": doc_id}),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        count += 1
        if count % 1000 == 0:
            print(f"Published {count} tasks...")

    print(f"Finished publishing {count} tasks to queue '{MIGRATE_QUEUE_NAME}'.")
    connection.close()

def worker():
    try:
        s3_client = get_s3_client()
    except ValueError as e:
        print(f"Error: {e}")
        return

    collection = get_mongo_collection()
    attachment_fields = ["images", "audios", "videos", "pdfs"]

    params = pika.URLParameters(RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = get_rabbitmq_channel(connection)
    channel.basic_qos(prefetch_count=1)

    print(f"Worker listening on queue '{MIGRATE_QUEUE_NAME}'. To exit press CTRL+C")

    def process_message(ch, method, properties, body):
        try:
            payload = json.loads(body)
            doc_id = payload.get("doc_id")
            if not doc_id:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            doc = collection.find_one({"_id": ObjectId(doc_id)})
            if not doc:
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            updated = False
            
            for field in attachment_fields:
                if field in doc and isinstance(doc[field], list):
                    for idx, item in enumerate(doc[field]):
                        # Handle dua format: dictionary dengan metadata atau string URL
                        if isinstance(item, dict):
                            original_url = item.get("full_url") or item.get("src")
                            has_s3_url = "s3_url" in item
                        elif isinstance(item, str):
                            original_url = item
                            has_s3_url = False
                        else:
                            continue  # Skip jika bukan dict atau string
                        
                        if original_url and not has_s3_url:
                            try:
                                # 1. Download file dari URL lama
                                response = requests.get(original_url, stream=True, timeout=30)
                                response.raise_for_status()
                                
                                # Parse nama file dan path
                                parsed_url = urlparse(original_url)
                                path = unquote(parsed_url.path)
                                filename = os.path.basename(path)
                                
                                # Buat path S3 yang unik
                                s3_key = path.lstrip('/') 
                                if not s3_key:
                                    s3_key = f"attachments/{field}/{filename}"

                                content_type = response.headers.get('Content-Type') or mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                                
                                # 2. Upload file ke S3 Public
                                s3_client.upload_fileobj(
                                    response.raw,
                                    S3_BUCKET_NAME,
                                    s3_key,
                                    ExtraArgs={
                                        'ContentType': content_type,
                                        'ACL': 'public-read' 
                                    }
                                )
                                
                                # 3. Bentuk URL AWS S3 yang baru
                                s3_url = f"https://{S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
                                
                                # Simpan s3_url ke item (handle dua format: dict atau string)
                                if isinstance(item, dict):
                                    item["s3_url"] = s3_url
                                elif isinstance(item, str):
                                    # Convert string ke dictionary format agar bisa simpan s3_url
                                    doc[field][idx] = {
                                        "src": item,
                                        "full_url": item,
                                        "s3_url": s3_url
                                    }
                                
                                updated = True
                                print(f"[OK] {doc_id} - Migrated: {original_url} -> {s3_url}")
                                
                            except Exception as e:
                                print(f"[ERROR] {doc_id} - Failed migrating {original_url}: {e}")

            # Jika ada update, simpan ke mongodb
            if updated:
                update_data = {field: doc[field] for field in attachment_fields if field in doc}
                collection.update_one({"_id": ObjectId(doc_id)}, {"$set": update_data})
            
            # Acknowledge task sukses dan selesai
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[ERROR] Unexpected worker error: {e}")
            # Reject task agar bisa di-requeue jika terjadi error fatal
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    channel.basic_consume(queue=MIGRATE_QUEUE_NAME, on_message_callback=process_message)
    
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\nStopping worker...")
        channel.stop_consuming()
    finally:
        if connection.is_open:
            connection.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate attachments to S3 via RabbitMQ worker")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    publish_parser = subparsers.add_parser("publish", help="Publish documents to RabbitMQ queue")
    publish_parser.add_argument("--limit", type=int, help="Limit jumlah dokumen yang di-publish (untuk testing)")
    subparsers.add_parser("worker", help="Consume from RabbitMQ queue and migrate attachments to S3")
    
    args = parser.parse_args()
    
    if args.command == "publish":
        publish_tasks(limit=args.limit)
    elif args.command == "worker":
        worker()
