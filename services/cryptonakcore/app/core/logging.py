import logging
import sys
import json

def setup_logging():
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log = {
                "level": record.levelname,
                "message": record.getMessage(),
                "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "logger": record.name,
            }
            return json.dumps(log)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
