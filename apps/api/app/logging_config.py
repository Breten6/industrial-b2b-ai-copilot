import json
import logging
from datetime import UTC, datetime


class EventFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "event": record.getMessage(),
        }
        for field in ("endpoint", "status", "attempt", "document_id", "page_count",
                      "candidate_count", "assertion_id", "action", "error_type"):
            if hasattr(record, field):
                event[field] = getattr(record, field)
        return json.dumps(event)


def configure_logging() -> None:
    logger = logging.getLogger("app")
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
