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

chroot_dir = path.join(path.dirname(path.abspath(__file__)), 'chroot')
MB = 1024 * 1024

class Snekbox(object):

    def python3(self, cmd):
        args = ['nsjail',
                '-Mo',
                '--chroot', chroot_dir,
                '-E', 'LANG=en_US.UTF-8',
                '-R/usr',
                '-R/lib',
                '-R/lib64',
                '--user', 'nobody',
                '--group', 'nogroup',
                '--time_limit', '2',
                '--disable_proc',
                '--iface_no_lo',
                '--cgroup_mem_max', str(50 * MB),
                '--cgroup_pids_max', '1',
                '--quiet', '--',
                '/usr/bin/python3', '-ISq', '-c', cmd]

        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                universal_newlines=True)

        stdout, stderr = proc.communicate()
        log.debug(stderr)
        log.debug(stdout)
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
        self.execute(body)
        #p = multiprocessing.Process(target=self.execute, args=(body,))
        #p.daemon = True
        #p.start()
        #t = threading.Thread(target=self.stopwatch, args=(p,))
        #t.daemon = True
        #t.start()

        ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    try:
        rmq = Rmq()
        snkbx = Snekbox()
        rmq.consume(callback=snkbx.message_handler)
    except KeyboardInterrupt:
        print("Exited")
        exit(0)
