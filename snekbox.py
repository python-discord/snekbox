import sys
import io
import json

from rmq.consumer import consume
from rmq.publisher import publish

from config import HOST
from config import EXCHANGE_TYPE
from config import QUEUE


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

    print(f"incoming: {msg}", flush=True)
    snek_msg = json.loads(msg)

    for snekid, snekcode in snek_msg.items():
        result = execute(snekcode)
        print(f"outgoing: {result}", flush=True)
        publish(result,
                host=HOST,
                queue=snekid,
                routingkey=snekid,
                exchange=snekid,
                exchange_type=EXCHANGE_TYPE)

    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    consume(host=HOST, queue=QUEUE, callback=message_handler)
