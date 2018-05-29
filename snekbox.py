import sys
import io
import json
import multiprocessing
import threading
import time
import re
import yaml

from logs import log
from rmq import Rmq


class Snekbox(object):

    def match_pattern(self, snek_code, expr):
        pattern = re.compile(expr)
        result = pattern.findall(snek_code)

        return result

    def load_filter(self):
        with open('filter.yml', 'r') as f:
            filter_file = f.read()
        filters = yaml.safe_load(filter_file)

        return filters

    def security_filter(self, snek_code):
        filters = self.load_filter()

        for rule in filters.get('filter'):
            if 'regex' in rule.get('type', []):
                result = self.match_pattern(snek_code, rule.get('name'))
                log.debug(result)

            if result:
                log.warn(f"security warning: {rule.get('comment')}")
                return False

        return True

    def execute(self, body):
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
        self.security_filter(snekcode)

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

    def stopwatch(self, process):
        log.debug(f"10 second timer started for process {process.pid}")
        for _ in range(10):
            time.sleep(1)
            if not process.is_alive():
                log.debug(f"Clean exit on process {process.pid}")
                exit(0)

        process.terminate()
        log.debug(f"Terminated process {process.pid} forcefully")

    def message_handler(self, ch, method, properties, body, thread_ws=None):
        p = multiprocessing.Process(target=self.execute, args=(body,))
        p.daemon = True
        p.start()

        t = threading.Thread(target=self.stopwatch, args=(p,))
        t.daemon = True
        t.start()

        ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    try:
        rmq = Rmq()
        snkbx = Snekbox()
        rmq.consume(callback=snkbx.message_handler)
    except KeyboardInterrupt:
        print("Exited")
        exit(0)
