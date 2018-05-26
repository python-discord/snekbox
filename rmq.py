import pika
import time
import traceback
import logging
import sys

from pika.exceptions import ConnectionClosed

from config import USERNAME
from config import PASSWORD
from config import HOST
from config import PORT
from config import EXCHANGE_TYPE
from config import QUEUE
from config import ROUTING_KEY
from config import EXCHANGE

from logs import log


class Rmq(object):

    def __init__(self,
                 username=USERNAME,
                 password=PASSWORD,
                 host=HOST,
                 port=PORT,
                 exchange_type=EXCHANGE_TYPE):

        self.username = USERNAME
        self.password = PASSWORD
        self.host = HOST
        self.port = PORT
        self.exchange_type = EXCHANGE_TYPE
        self.credentials = pika.PlainCredentials(self.username, self.password)
        self.con_params = pika.ConnectionParameters(self.host, self.port, '/', self.credentials)
        self.properties = pika.BasicProperties(content_type='text/plain', delivery_mode=1)

    def consume(self, queue=QUEUE, callback=None, thread_ws=None):

        while True:
            try:
                connection = pika.BlockingConnection(self.con_params)

                try:
                    channel = connection.channel()
                    channel.queue_declare(queue=queue, durable=False)
                    channel.basic_qos(prefetch_count=1)
                    channel.basic_consume(
                        lambda ch, method, properties, body: callback(ch, method, properties, body, thread_ws=thread_ws),
                        queue=queue)

                    log.info(f"Connected to host: {self.host} port: {self.port} queue: {queue}")

                    channel.start_consuming()

                except Exception:
                    exc = traceback.format_exc()
                    log.info(exc)

                finally:
                    connection.close()

            except ConnectionClosed:
                log.info(f"Connection lost, reconnecting to {self.host}")

            time.sleep(2)

    def publish(self,
                message,
                queue=QUEUE,
                routingkey=ROUTING_KEY,
                exchange=EXCHANGE):

        connection = pika.BlockingConnection(pika.ConnectionParameters(self.host, self.port, '/', self.credentials))
        channel = connection.channel()
        channel.queue_declare(queue=queue, durable=False)
        channel.exchange_declare(exchange=exchange, exchange_type=self.exchange_type)
        channel.queue_bind(exchange=exchange, queue=queue, routing_key=routingkey)

        result = channel.basic_publish(
            exchange=exchange,
            routing_key=routingkey,
            body=message,
            properties=self.properties
        )

        if result:
            log.info(f"Connecting to host: {self.host} port: {self.port} exchange: {exchange} queue: {queue}")
        else:
            log.info("not delivered")

        connection.close()
