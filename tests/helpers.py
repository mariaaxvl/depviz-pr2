"""Вспомогательные функции тестов."""
import os
import tempfile

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(TESTS_DIR, "data")


def write_temp(test, text, suffix=".csv"):
    """Создаёт временный файл с текстом; удаляется после теста."""
    handle, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(handle, "w", encoding="utf-8") as stream:
        stream.write(text)
    test.addCleanup(os.remove, path)
    return path
