import logging
from datetime import datetime
from .interfaces import ILogsService

logger = logging.getLogger(__name__)

class LogsEngine(ILogsService):
    def __init__(self):
        self._events = []
        self._max_events = 100

    def add_event(self, level: str, source: str, message: str):
        event = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "level": level.upper(),
            "source": source,
            "message": message
        }
        self._events.append(event)
        if len(self._events) > self._max_events:
            self._events.pop(0)
        
        log_msg = f"[{event['timestamp']}] [{source}] {message}"
        if level == "ERROR": logger.error(log_msg)
        elif level == "WARNING": logger.warning(log_msg)
        else: logger.info(log_msg)

    def get_recent_logs(self, count: int = 20) -> list:
        return self._events[-count:]
