import sys
import io
import json

from logs import log
from rmq import Rmq

rmq = Rmq()


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


def message_handler(ch, method, properties, body, thread_ws=None):
    msg = body.decode('utf-8')

    log.info(f"incoming: {msg}")
    snek_msg = json.loads(msg)

    for snekid, snekcode in snek_msg.items():
        result = execute(snekcode)
        log.info(f"outgoing: {result}")
        rmq.publish(result,
                    queue=snekid,
                    routingkey=snekid,
                    exchange=snekid)
    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    rmq.consume(callback=message_handler)
