import traceback
import sys
import time
import pika
import io

from rmq.consumer import consume
from rmq.publisher import publish

from config import USERNAME
from config import PASSWORD
from config import HOST
from config import PORT
from config import EXCHANGE
from config import EXCHANGE_TYPE
from config import QUEUE
from config import RETURN_QUEUE
from config import RETURN_EXCHANGE
from config import RETURN_ROUTING_KEY

def execute(snippet):
    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()
    failed = False
    try:
        exec(snippet)
    except Exception as e:
        failed = str(e)
    finally:
        sys.stdout = old_stdout

    if failed:
        return failed.strip()
    return redirected_output.getvalue().strip()


def message_handler(ch, method, properties, body):
    msg = body.decode('utf-8')

    # Execute code snippets here
    print(f"incoming: {msg}", flush=True)
    result = execute(msg)
    print(f"outgoing: {result}", flush=True)
    publish(result, host=HOST, queue=RETURN_QUEUE, routingkey=RETURN_ROUTING_KEY, exchange=RETURN_EXCHANGE, exchange_type=EXCHANGE_TYPE)

    ch.basic_ack(delivery_tag = method.delivery_tag)

if __name__ == '__main__':
    consume(host=HOST, queue=QUEUE, callback=message_handler)
