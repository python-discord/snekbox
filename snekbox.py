import json
import multiprocessing
import subprocess
import os
import sys

from rmq import Rmq


class Snekbox:
    """Core snekbox functionality, providing safe execution of Python code."""

    def __init__(self,
                 nsjail_binary='nsjail',
                 python_binary=os.path.dirname(sys.executable)+os.sep+'python3.6'):

        self.nsjail_binary = nsjail_binary
        self.python_binary = python_binary
        self._nsjail_workaround()

    env = {
        'PATH': (
            '/snekbox/.venv/bin:/usr/local/bin:/usr/local/'
            'sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'
        ),
        'LANG': 'en_US.UTF-8',
        'PYTHON_VERSION': '3.6.5',
        'PYTHON_PIP_VERSION': '10.0.1',
        'PYTHONDONTWRITEBYTECODE': '1',
    }

    def _nsjail_workaround(self):
        dirs = ['/sys/fs/cgroup/pids/NSJAIL', '/sys/fs/cgroup/memory/NSJAIL']
        for d in dirs:
            if not os.path.exists(d):
                os.makedirs(d)

    def python3(self, cmd):
        """
        Execute Python 3 code in a isolated environment.

        The value of ``cmd`` is passed using '-c' to a Python
        interpreter that is started in a ``nsjail``, isolating it
        from the rest of the system.

        Returns the output of executing the command (stdout) if
        successful, or a error message if the execution failed.
        """
        args = [self.nsjail_binary, '-Mo',
                '--rlimit_as', '700',
                '--chroot', '/',
                '-E', 'LANG=en_US.UTF-8',
                '-R/usr', '-R/lib', '-R/lib64',
                '--user', 'nobody',
                '--group', 'nogroup',
                '--time_limit', '2',
                '--disable_proc',
                '--iface_no_lo',
                '--cgroup_pids_max=1',
                '--cgroup_mem_max=52428800',
                '--quiet', '--',
                self.python_binary, '-ISq', '-c', cmd]
        try:
            proc = subprocess.Popen(args,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    env=self.env,
                                    universal_newlines=True)
        except ValueError:
            return 'ValueError: embedded null byte'

        stdout, stderr = proc.communicate()
        if proc.returncode == 0:
            output = stdout

        elif proc.returncode == 1:
            try:
                filtered = []
                for line in stderr.split('\n'):
                    if not line.startswith('['):
                        filtered.append(line)
                output = '\n'.join(filtered)
            except IndexError:
                output = ''

        elif proc.returncode == 109:
            return 'timed out or memory limit exceeded'

        elif proc.returncode == 255:
            return 'permission denied (root required)'

        elif proc.returncode:
            return f'unknown error, code: {proc.returncode}'

        else:
            return 'unknown error, no error code'

        return output

    def execute(self, body):
        """
        Handles execution of a raw JSON-formatted RMQ message, contained in ``body``.

        The message metadata, including the Python code to be executed, is
        extracted from the message body. The code is then executed in the
        isolated environment, and the results of the execution published
        to RMQ. Once published, the system exits, since the snekboxes
        are created and disposed of per-execution.
        """
        msg = body.decode('utf-8')
        result = ''
        snek_msg = json.loads(msg)
        snekid = snek_msg['snekid']
        snekcode = snek_msg['message'].strip()

        result = self.python3(snekcode)

        rmq.publish(result,
                    queue=snekid,
                    routingkey=snekid,
                    exchange=snekid)
        exit(0)

    def message_handler(self, ch, method, properties, body, thread_ws=None):
        """Spawns a daemon process that handles RMQ messages."""
        p = multiprocessing.Process(target=self.execute, args=(body,))
        p.daemon = True
        p.start()

        ch.basic_ack(delivery_tag=method.delivery_tag)


if __name__ == '__main__':
    try:
        rmq = Rmq()
        snkbx = Snekbox()
        rmq.consume(callback=snkbx.message_handler)
    except KeyboardInterrupt:
        print('Exited')
        exit(0)
