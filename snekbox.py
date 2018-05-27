import sys
import io
import json
import multiprocessing
import threading
import time

from logs import log
from rmq import Rmq

rmq = Rmq()


def execute(body):
    msg = body.decode('utf-8')
    log.info(f"incoming: {msg}")

    failed = False

    old_stdout = sys.stdout
    old_stderr = sys.stderr
    redirected_output = sys.stdout = io.StringIO()
    redirected_error = sys.stderr = io.StringIO()
    snek_msg = json.loads(msg)
    snekid = snek_msg['snekid']
    snekcode = snek_msg['message'].strip()

    try:
        exec(snekcode)

    except Exception as e:
        failed = str(e)

    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    if failed:
        result = failed.strip()
        log.debug(f"this was captured via exception: {result}")

    result_err = redirected_error.getvalue().strip()
    result_ok = redirected_output.getvalue().strip()

    if result_err:
        log.debug(f"this was captured via stderr: {result_err}")
        result = result_err
    if result_ok:
        result = result_ok

    log.info(f"outgoing: {result}")

    rmq.publish(result,
                queue=snekid,
                routingkey=snekid,
                exchange=snekid)
    exit(0)

def stopwatch(process):
    log.debug(f"10 second timer started for process {process.pid}")
    for _ in range(10):
        time.sleep(1)
        if not process.is_alive():
            log.debug(f"Clean exit on process {process.pid}")
            exit(0)

    process.terminate()
    log.debug(f"Rerminated process {process.pid} forcefully")

def message_handler(ch, method, properties, body, thread_ws=None):
    p = multiprocessing.Process(target=execute, args=(body,))
    p.daemon = True
    p.start()

    t = threading.Thread(target=stopwatch, args=(p,))
    t.daemon = True
    t.start()

    ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    rmq.consume(callback=message_handler)
