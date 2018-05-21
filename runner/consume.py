import pika
import traceback
import sys
from io import StringIO

from config import (
    USERNAME,
    PASSWORD,
    HOST,
    PORT,
    EXCHANGE,
    EXCHANGE_TYPE,
    QUEUE,
    ROUTING_KEY,
)

def execute(snippet):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = StringIO()
    failed = False
    try:
        exec(snippet)
    except Exception as e:
        failed = e
    finally:
        sys.stdout = old_stdout

    if failed:
        return failed
    return redirected_output.getvalue()


def message_handler(ch, method, properties, body):
    msg = body.decode('utf-8')

    # Execute code snippets here
    print(f"incoming: {msg}", flush=True)
    result = execute(msg)
    print(result, flush=True)

    ch.basic_ack(delivery_tag = method.delivery_tag)

def rabbitmq_consume():
    credentials = pika.PlainCredentials(USERNAME, PASSWORD)
    connection = pika.BlockingConnection(pika.ConnectionParameters(HOST, PORT, '/', credentials))

    channel = connection.channel()
    channel.queue_declare(queue=QUEUE, durable=False)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(message_handler, queue=QUEUE)

    try:
        print(f"""Connecting to
            host: {HOST}
            port: {PORT}
            exchange: {EXCHANGE}
            queue: {QUEUE}""", flush=True)

        channel.start_consuming()

    except Exception:
        exc = traceback.format_exc()
        print(exc, flush=True)

    finally:
        connection.close()

rabbitmq_consume()
