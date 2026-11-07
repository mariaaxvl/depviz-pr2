"""Тесты построения графа зависимостей."""
import unittest

from filerepo import FileRepository
from graph import GraphError, build_graph, describe
from helpers import write_temp
from maven import MavenRepository
from test_maven import APP, BASE_URL, local_fetch


ALPHABET_SIZE = 26
CHAIN_LENGTH = 3000


def letters(number):
    """Уникальное имя из заглавных латинских букв для номера."""
    name, value = "", number + 1
    while value:
        value, rest = divmod(value - 1, ALPHABET_SIZE)
        name = chr(ord("A") + rest) + name
    return name


class GraphTest(unittest.TestCase):
    """Проверки DFS, циклов и фильтра на тестовом репозитории."""

    def graph(self, text, root="A", substring=""):
        """Строит граф по описанию из текста."""
        repo = FileRepository(write_temp(self, text, ".txt"))
        return build_graph(repo, root, substring)

    def test_transitive(self):
        """Учитываются транзитивные зависимости."""
        graph = self.graph("A: B\nB: C\nC: D\nD:\n")
        self.assertEqual(list(graph.edges), ["A", "B", "C", "D"])

    def test_diamond_visited_once(self):
        """Общая зависимость обходится один раз."""
        graph = self.graph("A: B C\nB: D\nC: D\nD:\n")
        self.assertEqual(graph.edges["C"], ["D"])
        self.assertEqual(len(graph.edges), 4)
        self.assertEqual(graph.edge_count(), 4)

    def test_cycle(self):
        """Цикл находится, обход завершается."""
        graph = self.graph("A: B\nB: C\nC: A\n")
        self.assertEqual(graph.cycles, [["A", "B", "C", "A"]])

    def test_self_loop(self):
        """Зависимость пакета от самого себя - цикл."""
        graph = self.graph("A: A B\nB:\n")
        self.assertEqual(graph.cycles, [["A", "A"]])

    def test_inner_cycle(self):
        """Цикл не через корень."""
        graph = self.graph("A: B C\nB: D\nC: D\nD: B\n")
        self.assertEqual(graph.cycles, [["B", "D", "B"]])

    def test_filter(self):
        """Пакеты с подстрокой в имени исключаются вместе с поддеревом."""
        graph = self.graph("A: B C\nB: D\nC:\nD:\n", substring="B")
        self.assertEqual(list(graph.edges), ["A", "C"])
        self.assertEqual(graph.skipped, ["B"])

    def test_filter_root(self):
        """Корневой пакет, исключённый фильтром, - ошибка."""
        with self.assertRaisesRegex(GraphError, "исключён"):
            self.graph("A:\n", substring="A")

    def test_deep_graph(self):
        """Слишком глубокий граф - GraphError, а не падение."""
        lines = [f"{letters(i)}: {letters(i + 1)}"
                 for i in range(CHAIN_LENGTH)]
        repo = FileRepository(write_temp(self, "\n".join(lines), ".txt"))
        with self.assertRaises(GraphError):
            build_graph(repo, letters(0))

    def test_describe(self):
        """Отчёт содержит рёбра и сведения о циклах."""
        text = describe(self.graph("A: B\nB: A\n"), "A")
        self.assertIn("A -> B", text)
        self.assertIn("A -> B -> A", text)


class MavenGraphTest(unittest.TestCase):
    """Граф для Maven-репозитория (тестовые POM)."""

    def setUp(self):
        """Создаёт репозиторий поверх тестовых файлов."""
        self.repo = MavenRepository(BASE_URL, local_fetch)

    def test_app_graph(self):
        """Транзитивные зависимости app."""
        graph = build_graph(self.repo, APP)
        self.assertIn("org.demo:util:1.0", graph.edges)
        self.assertEqual(graph.cycles, [])

    def test_maven_cycle(self):
        """Цикл между пакетами Maven."""
        graph = build_graph(self.repo, "com.example:root:1.0")
        self.assertEqual(len(graph.cycles), 1)

    def test_maven_filter(self):
        """Фильтр по подстроке имени."""
        graph = build_graph(self.repo, APP, "lib-c")
        self.assertNotIn("com.example:lib-c:1.0", graph.edges)
