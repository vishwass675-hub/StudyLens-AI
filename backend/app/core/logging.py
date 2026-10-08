"""
Centralized structured logging and safe request tracing for StudyLens AI.
Ensures zero sensitive credential logging (API keys, Authorization headers, PDF blobs).
"""

import time
import logging
import sys
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Configure root and application loggers
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("studylens")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware tracing every API request safely.
    Logs method, route, duration (ms), status, and error category without logging sensitive payloads.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Ignore noisy static documentation or favicon requests
        if request.url.path in ("/favicon.ico", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        start_time = time.perf_counter()
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Log request outcome
            if response.status_code >= 400:
                logger.warning(
                    f"{method} {path} - status={response.status_code} - {duration_ms}ms"
                )
            else:
                logger.info(
                    f"{method} {path} - status={response.status_code} - {duration_ms}ms"
                )
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                f"{method} {path} - FAILED with {exc.__class__.__name__}: {str(exc)} - {duration_ms}ms"
            )
            raise exc
