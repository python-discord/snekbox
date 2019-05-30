import logging

log = logging.getLogger("snekbox.api")


class LoggingMiddleware:
    """Log basic information about responses."""

    def process_response(self, req, resp, resource, req_succeeded):
        """Log the method, route, and status of a response."""
        log.info(f"{req.method} {req.relative_uri} {resp.status}")
