import traceback
import sys
import time
import pika
import io

from pika.exceptions import ConnectionClosed

from config import USERNAME
from config import PASSWORD
from config import HOST
from config import PORT
from config import EXCHANGE
from config import QUEUE

def execute(snippet):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
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

    while True:
        credentials = pika.PlainCredentials(USERNAME, PASSWORD)
        con_params = pika.ConnectionParameters(HOST, PORT, '/', credentials)

        try:
            connection = pika.BlockingConnection(con_params)

            try:
                channel = connection.channel()
                channel.queue_declare(queue=QUEUE, durable=False)
                channel.basic_qos(prefetch_count=1)
                channel.basic_consume(message_handler, queue=QUEUE)

                print(f"""Connected to \nhost:     {HOST}\nport:     {PORT}\nexchange: {EXCHANGE}\nqueue:    {QUEUE}""", flush=True)

                channel.start_consuming()

            except:
                exc = traceback.format_exc()
                print(exc, flush=True)

            finally:
                connection.close()

        except ConnectionClosed:
            print(f"Connection lost, reconnecting to {HOST}", flush=True)
            pass

        time.sleep(2)

if __name__ == '__main__':
    rabbitmq_consume()
