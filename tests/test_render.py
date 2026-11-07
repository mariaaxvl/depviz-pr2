"""Тесты визуализации: PlantUML, ASCII-дерево, PNG."""
import os
import unittest
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import threading

from filerepo import FileRepository
from graph import build_graph
from helpers import DATA_DIR
from render import (ALPHABET, PNG_SIGNATURE, RenderError, ascii_tree,
                    encode_plantuml, plantuml_text, render_png,
                    render_remote, save_file)

GRAPHS = os.path.join(DATA_DIR, "graphs")
FAKE_PNG = PNG_SIGNATURE + b"fake"


def graph_of(name, root="A"):
    """Граф зависимостей из тестового файла."""
    return build_graph(FileRepository(os.path.join(GRAPHS, name)), root)


def decode_plantuml(code):
    """Обратное преобразование encode_plantuml (для проверки)."""
    bits = "".join(f"{ALPHABET.index(char):06b}" for char in code)
    raw = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits) - 7, 8))
    return zlib.decompressobj(-zlib.MAX_WBITS).decompress(raw).decode()


class PlantUmlTest(unittest.TestCase):
    """Проверки текста диаграммы."""

    def test_nodes_and_edges(self):
        """Есть все вершины и рёбра, корень выделен."""
        text = plantuml_text(graph_of("simple.txt"), "A", "T")
        self.assertTrue(text.startswith("@startuml"))
        self.assertTrue(text.rstrip().endswith("@enduml"))
        self.assertIn('rectangle "A" as n0 #LightBlue', text)
        self.assertEqual(text.count("-->"), 4)

    def test_flip(self):
        """При flip стрелки направлены от зависящего пакета."""
        graph = build_graph(FileRepository(
            os.path.join(GRAPHS, "single.txt")), "A")
        graph.edges["A"] = ["B"]
        graph.edges["B"] = []
        text = plantuml_text(graph, "A", "T", flip=True)
        self.assertIn("n1 --> n0", text)

    def test_encode_roundtrip(self):
        """Кодирование обратимо: текст восстанавливается."""
        text = plantuml_text(graph_of("multi.txt"), "A", "Проверка")
        self.assertEqual(decode_plantuml(encode_plantuml(text)), text)


class AsciiTreeTest(unittest.TestCase):
    """Проверки ASCII-дерева."""

    def test_diamond(self):
        """Общая зависимость отмечается как повтор."""
        expected = "\n".join([
            "A",
            "|-- B",
            "|   `-- D",
            "`-- C",
            "    `-- D (повтор)",
        ])
        self.assertEqual(ascii_tree(graph_of("simple.txt"), "A"), expected)

    def test_cycle_mark(self):
        """Цикл помечается и не раскрывается."""
        text = ascii_tree(graph_of("cycle.txt"), "A")
        self.assertIn("`-- A (цикл)", text)

    def test_single(self):
        """Дерево из одного пакета."""
        self.assertEqual(ascii_tree(graph_of("single.txt"), "A"), "A")


class PngTest(unittest.TestCase):
    """Проверки получения PNG."""

    def test_remote_used_without_plantuml(self):
        """Без установленного plantuml используется сервер."""
        data = render_png("x", which=lambda _: None,
                          remote=lambda _: FAKE_PNG)
        self.assertEqual(data, FAKE_PNG)

    def test_local_preferred(self):
        """Установленный plantuml имеет приоритет."""
        data = render_png("x", which=lambda _: "plantuml",
                          local=lambda text, exe: FAKE_PNG)
        self.assertEqual(data, FAKE_PNG)

    def test_not_png(self):
        """Ответ без сигнатуры PNG - ошибка."""
        with self.assertRaisesRegex(RenderError, "не PNG"):
            render_png("x", which=lambda _: None, remote=lambda _: b"oops")

    def test_unreachable_server(self):
        """Недоступный сервер - RenderError."""
        with self.assertRaisesRegex(RenderError, "нет доступа"):
            render_remote("x", server="http://127.0.0.1:1/")

    def test_http_server_roundtrip(self):
        """Запрос к серверу содержит закодированную диаграмму."""
        seen = []

        class Handler(BaseHTTPRequestHandler):
            """Отвечает PNG на любой GET-запрос."""

            def do_GET(self):
                """Запоминает путь запроса и отдаёт PNG."""
                seen.append(self.path)
                self.send_response(200)
                self.end_headers()
                self.wfile.write(FAKE_PNG)

            def log_message(self, *args):
                """Не печатает журнал запросов."""
                return None

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f"http://127.0.0.1:{server.server_address[1]}/png/"
        self.assertEqual(render_remote("@startuml\n@enduml\n", url), FAKE_PNG)
        self.assertTrue(seen[0].startswith("/png/"))

    def test_save_file(self):
        """Файл сохраняется в новом каталоге."""
        import shutil
        import tempfile
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "sub", "g.png")
        save_file(path, FAKE_PNG)
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(), FAKE_PNG)
