"""Тесты командной строки: вывод и коды возврата."""
import contextlib
import functools
import io
import os
import unittest

from helpers import DATA_DIR, start_repo_server, write_temp
from main import main
from test_config import make_csv

REPO_DIR = os.path.join(DATA_DIR, "maven_repo")


def run_main(path, *extra):
    """Запускает main с конфигом; возвращает (код, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main([path, "--no-image", *extra])
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    """Проверки вывода зависимостей и обработки ошибок."""

    @functools.cached_property
    def url(self):
        """URL локального репозитория (сервер запускается при первом вызове)."""
        return start_repo_server(self, REPO_DIR)

    def run_with(self, **overrides):
        """Запускает main с конфигурацией BASE и заменами."""
        overrides.setdefault("repo", self.url)
        return run_main(write_temp(self, make_csv(overrides)))

    def test_prints_graph(self):
        """Выводится граф с транзитивными зависимостями."""
        code, out, err = self.run_with()
        self.assertEqual(code, 0)
        self.assertIn("com.example:lib-c:1.0 -> org.demo:util:1.0", out)
        self.assertIn("ghost", err)

    def test_no_dependencies(self):
        """Пакет без зависимостей."""
        code, out, _ = self.run_with(package="com.example:managed:3.0")
        self.assertIn("(нет зависимостей)", out)

    def test_unknown_package(self):
        """Неизвестный пакет - код 3."""
        code, _, err = self.run_with(package="com.example:nope:1.0")
        self.assertEqual(code, 3)
        self.assertIn("Ошибка репозитория", err)

    def test_bad_config(self):
        """Ошибка конфигурации - код 2."""
        code, _, err = self.run_with(output="x.jpg")
        self.assertEqual(code, 2)
        self.assertIn("Ошибка конфигурации", err)


class TestModeTest(unittest.TestCase):
    """Проверки тестового режима и ошибок графа."""

    def run_graph(self, graph, package="A", substring=""):
        """Запускает main для тестового репозитория из файла."""
        path = os.path.join(DATA_DIR, "graphs", graph)
        text = make_csv({"package": package, "repo": path,
                         "test_mode": "true", "filter": substring})
        return run_main(write_temp(self, text))

    def test_graph_output(self):
        """Выводятся рёбра графа."""
        code, out, _ = self.run_graph("simple.txt")
        self.assertEqual(code, 0)
        self.assertIn("A -> B, C", out)
        self.assertIn("Циклических зависимостей не найдено", out)

    def test_cycle_output(self):
        """Выводится информация о цикле."""
        _, out, _ = self.run_graph("cycle.txt")
        self.assertIn("A -> B -> C -> A", out)

    def test_filter_output(self):
        """Выводятся исключённые пакеты."""
        _, out, _ = self.run_graph("multi.txt", substring="F")
        self.assertIn("Исключены фильтром: F", out)

    def test_unknown_package(self):
        """Пакет отсутствует в тестовом репозитории - код 3."""
        code, _, err = self.run_graph("simple.txt", package="Z")
        self.assertEqual(code, 3)
        self.assertIn("не найден", err)

    def test_filter_root(self):
        """Корень исключён фильтром - код 4."""
        code, _, err = self.run_graph("simple.txt", substring="A")
        self.assertEqual(code, 4)
        self.assertIn("Ошибка графа", err)


class AsciiTreeCliTest(unittest.TestCase):
    """Параметр ascii_tree и ошибки визуализации."""

    def run_simple(self, ascii_tree):
        """Запускает main для simple.txt с заданным ascii_tree."""
        path = os.path.join(DATA_DIR, "graphs", "simple.txt")
        text = make_csv({"package": "A", "repo": path, "test_mode": "true",
                         "ascii_tree": ascii_tree})
        return run_main(write_temp(self, text))

    def test_tree_printed(self):
        """При ascii_tree=true выводится дерево."""
        _, out, _ = self.run_simple("true")
        self.assertIn("ASCII-дерево:", out)
        self.assertIn("`-- D (повтор)", out)

    def test_tree_not_printed(self):
        """При ascii_tree=false дерево не выводится."""
        _, out, _ = self.run_simple("false")
        self.assertNotIn("ASCII-дерево", out)
