import sys
import io
import json
import multiprocessing

from logs import log
from rmq import Rmq

rmq = Rmq()


def execute(body):
    msg = body.decode('utf-8')
    log.info(f"incoming: {msg}")

    failed = False

    old_stdout = sys.stdout
    redirected_output = sys.stdout = io.StringIO()

    try:

        snek_msg = json.loads(msg)
        for snekid, snekcode in snek_msg.items():
            exec(snekcode)

    except Exception as e:
        failed = str(e)

    finally:
        sys.stdout = old_stdout

    if failed:
        result = failed.strip()

    result = redirected_output.getvalue().strip()

    log.info(f"outgoing: {result}")

    rmq.publish(result,
                queue=snekid,
                routingkey=snekid,
                exchange=snekid)
    exit(0)


def message_handler(ch, method, properties, body, thread_ws=None):
    p = multiprocessing.Process(target=execute, args=(body,))
    p.daemon = True
    p.start()

    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    rmq.consume(callback=message_handler)
