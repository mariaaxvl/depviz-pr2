"""Тесты обратных зависимостей."""
import os
import unittest

from filerepo import FileRepository
from graph import (GraphError, build_full_graph, describe_reverse, invert,
                   reverse_graph)
from helpers import DATA_DIR, write_temp
from maven import MavenRepository
from test_cli import run_main
from test_config import make_csv
from test_maven import BASE_URL, local_fetch

SIMPLE = os.path.join(DATA_DIR, "graphs", "simple.txt")
CYCLE = os.path.join(DATA_DIR, "graphs", "cycle.txt")
SINGLE = os.path.join(DATA_DIR, "graphs", "single.txt")


def reverse_of(path, target, substring=""):
    """Граф обратных зависимостей target в тестовом репозитории."""
    repo = FileRepository(path)
    full = build_full_graph(repo, repo.packages(), substring)
    return reverse_graph(full, target)


class ReverseTest(unittest.TestCase):
    """Проверки обхода по обращённым рёбрам."""

    def test_invert(self):
        """Рёбра обращаются."""
        graph = build_full_graph(FileRepository(SIMPLE), ["A"])
        self.assertEqual(invert(graph)["D"], ["B", "C"])

    def test_transitive_dependents(self):
        """Находятся прямые и транзитивные зависящие пакеты."""
        graph = reverse_of(SIMPLE, "D")
        self.assertEqual(list(graph.edges), ["D", "B", "A", "C"])
        self.assertEqual(graph.edges["D"], ["B", "C"])

    def test_nobody_depends(self):
        """От корневого пакета никто не зависит."""
        graph = reverse_of(SIMPLE, "A")
        self.assertEqual(graph.edges, {"A": []})

    def test_single(self):
        """Единственный пакет."""
        self.assertEqual(reverse_of(SINGLE, "A").edges, {"A": []})

    def test_cycle(self):
        """Обратный обход тоже находит циклы."""
        graph = reverse_of(CYCLE, "A")
        self.assertEqual(graph.cycles, [["A", "C", "B", "A"]])

    def test_filter(self):
        """Исключённые пакеты не участвуют."""
        graph = reverse_of(SIMPLE, "D", "B")
        self.assertNotIn("B", graph.edges)

    def test_unknown_target(self):
        """Пакета нет в графе - GraphError."""
        with self.assertRaisesRegex(GraphError, "отсутствует"):
            reverse_of(SIMPLE, "Z")

    def test_describe(self):
        """В отчёте есть стрелки <-."""
        text = describe_reverse(reverse_of(SIMPLE, "D"), "D")
        self.assertIn("D <- B, C", text)
        self.assertIn("A <- (никто не зависит)", text)


class MavenReverseTest(unittest.TestCase):
    """Обратные зависимости для Maven: корни задаёт universe."""

    def test_dependents_of_lib_c(self):
        """От lib-c зависят lib-a, lib-b, app и root."""
        repo = MavenRepository(BASE_URL, local_fetch)
        full = build_full_graph(repo, ["com.example:root:1.0"])
        graph = reverse_graph(full, "com.example:lib-c:1.0")
        names = {node.split(":")[1] for node in graph.edges}
        self.assertEqual(names, {"lib-c", "lib-a", "lib-b", "app", "root"})


class ReverseCliTest(unittest.TestCase):
    """Режим reverse в командной строке."""

    def run_reverse(self, package, **extra):
        """Запускает main в режиме reverse на тестовом репозитории."""
        values = {"package": package, "repo": SIMPLE, "test_mode": "true",
                  "reverse": "true"}
        values.update(extra)
        return run_main(write_temp(self, make_csv(values)))

    def test_output(self):
        """Выводится отчёт об обратных зависимостях."""
        code, out, _ = self.run_reverse("D")
        self.assertEqual(code, 0)
        self.assertIn("Обратные зависимости пакета D", out)

    def test_unknown_package(self):
        """Неизвестный пакет - код 4."""
        code, _, err = self.run_reverse("Z")
        self.assertEqual(code, 4)
        self.assertIn("Ошибка графа", err)
