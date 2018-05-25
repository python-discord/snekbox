import time
import traceback
import pika
from pika.exceptions import ConnectionClosed


def consume(username='guest',
            password='guest',
            host='localhost',
            port=5672,
            queue='',
            callback=None):

    while True:
        credentials = pika.PlainCredentials(username, password)
        con_params = pika.ConnectionParameters(host, port, '/', credentials)

        try:
            connection = pika.BlockingConnection(con_params)

            try:
                channel = connection.channel()
                channel.queue_declare(queue=queue, durable=False)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(callback, queue=queue)

                print(f"""Connected to host: {host} port: {port} queue: {queue}""", flush=True)

                channel.start_consuming()

            except Exception:
                exc = traceback.format_exc()
                print(exc, flush=True)

            finally:
                connection.close()

        except ConnectionClosed:
            print(f"Connection lost, reconnecting to {host}", flush=True)
            pass

        time.sleep(2)
