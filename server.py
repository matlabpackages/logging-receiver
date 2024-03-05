"""Logging receiver server."""
import logging
import logging.handlers
import logging.config
import pickle
import select
import socketserver
import struct


class LogRecordStreamHandler(socketserver.StreamRequestHandler):
    """Handler for a streaming logging request.

    This basically logs the record using whatever logging policy is
    configured locally.
    """

    def handle(self):
        """
        Handle multiple requests - each expected to be a 4-byte length,
        followed by the LogRecord in pickle format. Logs the record
        according to whatever policy is configured locally.
        """
        while True:
            chunk = self.connection.recv(4)
            if len(chunk) < 4:
                break
            slen = struct.unpack('>L', chunk)[0]
            chunk = self.connection.recv(slen)
            while len(chunk) < slen:
                chunk = chunk + self.connection.recv(slen - len(chunk))
            obj = self._unpickle(chunk)
            record = logging.makeLogRecord(obj)
            self._handle_log_record(record)

    def _unpickle(self, data):
        """Decode log record in pickle format."""
        return pickle.loads(data)

    def _handle_log_record(self, record):
        """Handle log record."""
        # if a name is specified, we use the named logger rather than the one
        # implied by the record.
        if self.server.logname is not None:
            name = self.server.logname
        else:
            name = record.name
        logger = logging.getLogger(name)
        # N.B. EVERY record gets logged. This is because Logger.handle
        # is normally called AFTER logger-level filtering. If you want
        # to do filtering, do it at the client end to save wasting
        # cycles and network bandwidth!
        logger.handle(record)


class LogRecordSocketReceiver(socketserver.ThreadingTCPServer):
    """
    Simple TCP socket-based logging receiver suitable for testing.
    """

    allow_reuse_address = True

    def __init__(self, host='localhost',
                 port=logging.handlers.DEFAULT_TCP_LOGGING_PORT,
                 handler=LogRecordStreamHandler):
        socketserver.ThreadingTCPServer.__init__(self, (host, port), handler)
        self.abort = 0
        self.timeout = 1
        self.logname = None

    def serve_until_stopped(self):
        """Start server."""
        abort = 0
        while not abort:
            rd, _, _ = select.select(
                [self.socket.fileno()],
                [],
                [],
                self.timeout
            )
            if rd:
                self.handle_request()
            abort = self.abort


def main():
    """Main function."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {},
        "formatters": {
            "json": {
                "()": "json_formatter.JsonFormatter",
                "fmt_keys": {
                    "level": "levelname",
                    "message": "message",
                    "time": "time",
                    "logger": "name",
                    "module": "module",
                    "function": "funcName",
                    "line": "lineno",
                    "thread_name": "threadName"
                }
            },
            "console": {
                "format": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z"
            },
        },
        "handlers": {
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "DEBUG",
                "formatter": "json",
                "filename": "logs/log.jsonl",
                "maxBytes": 10000,
                "backupCount": 3
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "stream": "ext://sys.stderr",
                "formatter": "console",
            },
        },
        "loggers": {
            "root": {"level": "DEBUG", "handlers": ["file", "stderr"]}
        }
    }

    logging.config.dictConfig(config=logging_config)

    tcpserver = LogRecordSocketReceiver(port=9000)
    print('Starting TCP server.')
    tcpserver.serve_until_stopped()


if __name__ == '__main__':
    main()
