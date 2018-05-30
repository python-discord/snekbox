import sys
import io
import json
import multiprocessing
import threading
import time
from os import path
import subprocess

from logs import log
from rmq import Rmq


class Snekbox(object):
    env = {
        'PATH': '/snekbox/.venv/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
        'LANG': 'en_US.UTF-8',
        'PYTHON_VERSION': '3.6.5',
        'PYTHON_PIP_VERSION': '10.0.1',
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    def python3(self, cmd):
        args = ["nsjail", "-Mo",
                "--rlimit_as", "700",
                "--chroot", "/",
                "-E", "LANG=en_US.UTF-8",
                "-R/usr", "-R/lib", "-R/lib64",
                "--user", "nobody",
                "--group", "nogroup",
                "--time_limit", "2",
                "--disable_proc",
                "--iface_no_lo",
                "--quiet", "--", "/usr/local/bin/python3.6", "-ISq", "-c", cmd]

        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                env=self.env,
                                universal_newlines=True)

        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            output = stdout
        elif proc.returncode == 1:
            try:
                output = stderr.split('\n')[-2]
            except IndexError:
                output = ''
        elif proc.returncode == 109:
            output = 'timed out or memory limit exceeded'
        else:
            output = 'unknown error'
        return output

    def execute(self, body):
        msg = body.decode('utf-8')
        log.info(f"incoming: {msg}")
        result = ""
        snek_msg = json.loads(msg)
        snekid = snek_msg['snekid']
        snekcode = snek_msg['message'].strip()

        result = self.python3(snekcode)

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
