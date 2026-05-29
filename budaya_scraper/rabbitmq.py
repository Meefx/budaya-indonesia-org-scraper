from __future__ import annotations

import json
from typing import Any, Callable

import pika

from .config import Settings


class RabbitQueue:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.params = pika.URLParameters(settings.rabbitmq_url)

    def publish(self, message: dict[str, Any]) -> None:
        connection = pika.BlockingConnection(self.params)
        channel = connection.channel()
        channel.queue_declare(queue=self.settings.rabbitmq_queue, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=self.settings.rabbitmq_queue,
            body=json.dumps(message, ensure_ascii=False).encode("utf-8"),
            properties=pika.BasicProperties(content_type="application/json", delivery_mode=2),
        )
        connection.close()

    def consume(self, handler: Callable[[dict[str, Any]], None]) -> None:
        connection = pika.BlockingConnection(self.params)
        channel = connection.channel()
        channel.queue_declare(queue=self.settings.rabbitmq_queue, durable=True)
        channel.basic_qos(prefetch_count=1)

        def _callback(ch: pika.adapters.blocking_connection.BlockingChannel, method: Any, _: Any, body: bytes) -> None:
            payload = json.loads(body.decode("utf-8"))
            handler(payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        channel.basic_consume(queue=self.settings.rabbitmq_queue, on_message_callback=_callback)
        channel.start_consuming()
