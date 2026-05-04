import json
import logging
import time
import uuid


_RESERVED_LOG_RECORD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "message",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_") or key in _RESERVED_LOG_RECORD_ATTRS:
                continue
            payload[key] = _json_safe(value)

        return json.dumps(payload, separators=(",", ":"), ensure_ascii=True)


def _json_safe(value):
    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


class RequestLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.logger = logging.getLogger("bidals.requests")

    def __call__(self, request):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.request_id = request_id
        started_at = time.perf_counter()

        try:
            response = self.get_response(request)
        except Exception:
            if request.path.startswith("/api/"):
                self.logger.exception(
                    "api_request_error",
                    extra=self._log_extra(
                        request=request,
                        request_id=request_id,
                        started_at=started_at,
                        status_code=500,
                        event="api_request_error",
                    ),
                )
            raise

        response["X-Request-ID"] = request_id

        if request.path.startswith("/api/"):
            self.logger.info(
                "api_request",
                extra=self._log_extra(
                    request=request,
                    request_id=request_id,
                    started_at=started_at,
                    status_code=response.status_code,
                    event="api_request",
                ),
            )

        return response

    def _log_extra(self, *, request, request_id, started_at, status_code, event):
        user = getattr(request, "user", None)
        user_id = user.id if getattr(user, "is_authenticated", False) else None
        return {
            "event": event,
            "request_id": request_id,
            "method": request.method,
            "path": request.path,
            "status_code": status_code,
            "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
            "user_id": user_id,
        }
