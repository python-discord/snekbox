import concurrent.futures
import contextlib
import multiprocessing
from typing import Iterator

from gunicorn.app.base import Application


class _StandaloneApplication(Application):
    def __init__(self, config_path: str = None, **kwargs):
        self.config_path = config_path
        self.options = kwargs

        super().__init__()

    def init(self, parser, opts, args):
        pass

    def load(self):
        from snekbox.api.app import application
        return application

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings and value is not None:
                self.cfg.set(key.lower(), value)

        if self.config_path:
            self.load_config_from_file(self.config_path)


def _proc_target(config_path: str, event: multiprocessing.Event, **kwargs) -> None:
    """Run a Gunicorn app with the given config and set `event` when Gunicorn is ready."""
    def when_ready(_):
        event.set()

    app = _StandaloneApplication(config_path, when_ready=when_ready, **kwargs)

    import logging
    logging.disable(logging.INFO)

    app.run()


@contextlib.contextmanager
def run_gunicorn(config_path: str = "config/gunicorn.conf.py", **kwargs) -> Iterator[None]:
    """
    Run the Snekbox app through separate Gunicorn process. Use as a context manager.

    `config_path` is the path to the Gunicorn config to use.
    Additional kwargs are interpreted as Gunicorn settings.

    Raise RuntimeError if Gunicorn terminates before it is ready.
    Raise TimeoutError if Gunicorn isn't ready after 60 seconds.
    """
    event = multiprocessing.Event()
    proc = multiprocessing.Process(target=_proc_target, args=(config_path, event), kwargs=kwargs)

    try:
        proc.start()

        # Wait 60 seconds for Gunicorn to be ready, but exit early if Gunicorn fails.
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)
        concurrent.futures.wait(
            [executor.submit(proc.join), executor.submit(event.wait)],
            timeout=60,
            return_when=concurrent.futures.FIRST_COMPLETED
        )
        # Can't use the context manager cause wait=False needs to be set.
        executor.shutdown(wait=False, cancel_futures=True)

        if proc.is_alive():
            if not event.is_set():
                raise TimeoutError("Timed out waiting for Gunicorn to be ready.")
        else:
            raise RuntimeError(f"Gunicorn terminated unexpectedly with code {proc.exitcode}.")

        yield
    finally:
        proc.terminate()
