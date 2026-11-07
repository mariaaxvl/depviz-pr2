"""Вспомогательные функции тестов."""
import functools
import os
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TESTS_DIR, "data")


def write_temp(test, text, suffix=".csv"):
    """Создаёт временный файл с текстом; удаляется после теста."""
    handle, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(text)
    test.addCleanup(os.remove, path)
    return path


class QuietHandler(SimpleHTTPRequestHandler):
    """HTTP-обработчик без журнала запросов."""

    def log_message(self, *args):
        """Не печатает журнал запросов."""
        return None


def start_repo_server(test, directory):
    """Запускает локальный HTTP-сервер каталога; возвращает его URL."""
    handler = functools.partial(QuietHandler, directory=directory)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    test.addCleanup(server.server_close)
    test.addCleanup(server.shutdown)
    return f"http://127.0.0.1:{server.server_address[1]}"
