"""Визуализация графа: PlantUML, PNG и ASCII-дерево."""
import os
import shutil
import subprocess
import urllib.error
import urllib.request
import zlib

PLANTUML_SERVER = "https://www.plantuml.com/plantuml/png/"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
ALPHABET = ("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz-_")
COMPRESS_LEVEL = 9
ZLIB_HEADER = 2
ZLIB_TRAILER = 4
CHUNK = 3
TIMEOUT_SEC = 60
USER_AGENT = "depviz/1.0"
ROOT_COLOR = "#LightBlue"


class RenderError(Exception):
    """Ошибка визуализации графа."""


def plantuml_text(graph, root, title, flip=False):
    """Текст диаграммы PlantUML; flip рисует стрелки против рёбер графа."""
    ids = {node: f"n{number}" for number, node in enumerate(graph.edges)}
    lines = ["@startuml", f"title {title}", "skinparam shadowing false"]
    for node, alias in ids.items():
        color = " " + ROOT_COLOR if node == root else ""
        lines.append(f'rectangle "{node}" as {alias}{color}')
    for node, deps in graph.edges.items():
        for dep in deps:
            source, target = (dep, node) if flip else (node, dep)
            lines.append(f"{ids[source]} --> {ids[target]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def tree_note(node, path, seen):
    """Пометка узла дерева: цикл, повтор или пусто."""
    if node in path:
        return " (цикл)"
    if node in seen:
        return " (повтор)"
    return ""


def add_children(graph, node, prefix, path, seen, lines):
    """Рекурсивно добавляет строки ASCII-дерева для потомков узла."""
    deps = graph.edges.get(node, [])
    last_index = len(deps) - 1
    for index, dep in enumerate(deps):
        last = index == last_index
        note = tree_note(dep, path, seen)
        branch = "`-- " if last else "|-- "
        lines.append(f"{prefix}{branch}{dep}{note}")
        if not note:
            seen.add(dep)
            extension = "    " if last else "|   "
            add_children(graph, dep, prefix + extension, path + [dep],
                         seen, lines)


def ascii_tree(graph, root):
    """ASCII-дерево зависимостей; повторы и циклы помечаются."""
    lines = [root]
    try:
        add_children(graph, root, "", [root], {root}, lines)
    except RecursionError:
        raise RenderError("граф слишком глубокий для вывода дерева") from None
    return "\n".join(lines)


def encode_chunk(chunk):
    """Кодирует до трёх байт в четыре символа алфавита PlantUML."""
    first, second, third = chunk.ljust(CHUNK, b"\0")
    indices = (first >> 2,
               ((first & 3) << 4) | (second >> 4),
               ((second & 15) << 2) | (third >> 6),
               third & 63)
    return "".join(ALPHABET[index] for index in indices)


def encode_plantuml(text):
    """Кодирует текст диаграммы для URL сервера PlantUML (deflate+base64)."""
    packed = zlib.compress(text.encode("utf-8"), COMPRESS_LEVEL)
    packed = packed[ZLIB_HEADER:-ZLIB_TRAILER]
    return "".join(encode_chunk(packed[start:start + CHUNK])
                   for start in range(0, len(packed), CHUNK))


def render_remote(text, server=PLANTUML_SERVER):
    """Получает PNG от сервера PlantUML."""
    request = urllib.request.Request(
        server + encode_plantuml(text), headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEC) as reply:
            return reply.read()
    except urllib.error.HTTPError as err:
        raise RenderError(
            f"сервер PlantUML ответил ошибкой HTTP {err.code} "
            f"(слишком большой граф? установите plantuml)") from None
    except (urllib.error.URLError, OSError) as err:
        raise RenderError(
            f"нет доступа к серверу PlantUML ({err}); проверьте интернет "
            f"или установите plantuml") from None


def render_local(text, executable):
    """Получает PNG от установленной программы plantuml."""
    try:
        done = subprocess.run([executable, "-tpng", "-pipe"],
                              input=text.encode("utf-8"),
                              capture_output=True, timeout=TIMEOUT_SEC)
    except (OSError, subprocess.SubprocessError) as err:
        raise RenderError(f"не удалось запустить plantuml: {err}") from None
    if done.returncode:
        message = done.stderr.decode("utf-8", "replace").strip()
        raise RenderError(f"plantuml завершился с ошибкой: {message}")
    return done.stdout


def render_png(text, which=shutil.which, remote=render_remote,
               local=render_local):
    """PNG диаграммы: локальный plantuml, иначе сервер PlantUML."""
    executable = which("plantuml")
    data = local(text, executable) if executable else remote(text)
    if not data.startswith(PNG_SIGNATURE):
        raise RenderError("PlantUML вернул не PNG-изображение")
    return data


def save_file(path, data):
    """Записывает байты в файл, создавая каталоги."""
    try:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(data)
    except OSError as err:
        raise RenderError(f"не удалось записать {path}: {err}") from None
