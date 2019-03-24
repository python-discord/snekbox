import time
import traceback

import pika
from pika.exceptions import ConnectionClosed

from config import EXCHANGE, EXCHANGE_TYPE, HOST, PASSWORD, PORT, QUEUE, ROUTING_KEY, USERNAME
from logs import log


class Rmq:
    """Rabbit MQ (RMQ) implementation used for communication with the bot."""

    def __init__(self):
        self.credentials = pika.PlainCredentials(USERNAME, PASSWORD)
        self.con_params = pika.ConnectionParameters(HOST, PORT, '/', self.credentials)
        self.properties = pika.BasicProperties(content_type='text/plain', delivery_mode=1)

    def _declare(self, channel, queue):
        channel.queue_declare(
            queue=queue,
            durable=False,  # Do not commit messages to disk
            arguments={'x-message-ttl': 5000},  # Delete message automatically after x milliseconds
            auto_delete=True)  # Delete queue when all connection are closed

    def consume(self, queue=QUEUE, callback=None, thread_ws=None, run_once=False):
        """Subscribe to read from a RMQ channel."""
        while True:
            try:
                connection = pika.BlockingConnection(self.con_params)

                try:
                    channel = connection.channel()
                    self._declare(channel, queue)
                    channel.basic_qos(prefetch_count=1)

                    if not run_once:
                        channel.basic_consume(
                            lambda ch, method, properties, body:
                            callback(ch, method, properties, body, thread_ws=thread_ws),
                            queue=queue)

                    log.info(f"Connected to host: {HOST} port: {PORT} queue: {queue}")

                    if thread_ws:
                        if not thread_ws.closed:
                            thread_ws.send('{"service": "connected"}')

                    if run_once:
                        return channel.basic_get(queue=queue)

                    channel.start_consuming()

                except Exception:
                    exc = traceback.format_exc()
                    log.error(exc)

                finally:
                    connection.close()

            except ConnectionClosed:
                if thread_ws:
                    if not thread_ws.closed:
                        log.error(f"Connection to {HOST} could not be established")
                        thread_ws.send('{"service": "disconnected"}')
                        exit(1)

                log.error(f"Connection lost, reconnecting to {HOST}")

            time.sleep(2)

    def publish(self, message, queue=QUEUE, routingkey=ROUTING_KEY, exchange=EXCHANGE):
        """Open a connection to publish (write) to a RMQ channel."""

        try:
            connection = pika.BlockingConnection(self.con_params)

            try:
                channel = connection.channel()

                self._declare(channel, queue)

                channel.exchange_declare(
                    exchange=exchange,
                    exchange_type=EXCHANGE_TYPE)

                channel.queue_bind(
                    exchange=exchange,
                    queue=queue,
                    routing_key=routingkey)

                result = channel.basic_publish(
                    exchange=exchange,
                    routing_key=routingkey,
                    body=message,
                    properties=self.properties)

                if result:
                    return result

                else:
                    log.error(f"Message '{message}' not delivered")

            except ConnectionClosed:
                log.error(f"Could not send message, connection to {HOST} was lost")
                exit(1)

            finally:
                connection.close()

        except ConnectionClosed:
            log.error(f"Could not connect to {HOST}")
