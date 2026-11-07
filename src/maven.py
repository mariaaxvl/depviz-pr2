"""Получение прямых зависимостей Maven-пакета из POM-файлов репозитория."""
import re
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import namedtuple

TIMEOUT_SEC = 15
HTTP_NOT_FOUND = 404
COORD_PARTS = 3
MAX_PARENT_DEPTH = 20
MAX_PASSES = 10
VAR_RE = re.compile(r"\$\{([^}]+)\}")
INCLUDED_SCOPES = ("compile", "runtime")
DEFAULT_SCOPE = "compile"
RANGE_CHARS = "[]()"
USER_AGENT = "depviz/1.0"


class RepositoryError(Exception):
    """Ошибка получения данных из репозитория."""


class Coord(namedtuple("Coord", "group artifact version")):
    """Координаты пакета Maven: группа, артефакт, версия."""

    __slots__ = ()

    @classmethod
    def parse(cls, text):
        """Разбирает строку группа:артефакт:версия."""
        parts = text.split(":")
        if len(parts) != COORD_PARTS or not all(parts):
            raise RepositoryError(
                f"неверные координаты пакета '{text}' "
                f"(нужно группа:артефакт:версия)")
        return cls(*parts)

    def __str__(self):
        return ":".join(self)


def fetch_text(url):
    """Скачивает текст по URL; ошибки сети - RepositoryError."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SEC) as reply:
            return reply.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        if err.code == HTTP_NOT_FOUND:
            raise RepositoryError(f"не найден в репозитории: {url}") from None
        raise RepositoryError(f"ошибка HTTP {err.code}: {url}") from None
    except (urllib.error.URLError, OSError) as err:
        raise RepositoryError(
            f"репозиторий недоступен ({err}): {url}") from None
    except UnicodeDecodeError:
        raise RepositoryError(f"файл не в кодировке UTF-8: {url}") from None


def strip_namespaces(root):
    """Убирает пространства имён из тегов, чтобы искать по простым именам."""
    for element in root.iter():
        if isinstance(element.tag, str) and "}" in element.tag:
            element.tag = element.tag.split("}", 1)[1]


def child_text(element, name):
    """Текст дочернего элемента или пустая строка."""
    child = element.find(name)
    if child is None or not child.text:
        return ""
    return child.text.strip()


def children(element, name):
    """Список потомков вложенного элемента (пустой, если его нет)."""
    node = element.find(name) if element is not None else None
    return list(node) if node is not None else []


def raw_dependency(element):
    """Словарь с полями элемента <dependency> без разрешения свойств."""
    return {
        "group": child_text(element, "groupId"),
        "artifact": child_text(element, "artifactId"),
        "version": child_text(element, "version"),
        "scope": child_text(element, "scope"),
        "optional": child_text(element, "optional").lower(),
    }


class Pom:
    """Разобранный POM-файл: свойства, зависимости, управление версиями."""

    def __init__(self, root):
        """Извлекает нужные части дерева XML."""
        parent = root.find("parent")
        self.parent = None
        if parent is not None:
            self.parent = Coord(child_text(parent, "groupId"),
                                child_text(parent, "artifactId"),
                                child_text(parent, "version"))
        inherited = self.parent or Coord("", "", "")
        self.group = child_text(root, "groupId") or inherited.group
        self.artifact = child_text(root, "artifactId")
        self.version = child_text(root, "version") or inherited.version
        self.properties = {node.tag: (node.text or "").strip()
                           for node in children(root, "properties")}
        self.dependencies = [raw_dependency(node)
                             for node in children(root, "dependencies")]
        management = root.find("dependencyManagement")
        self.managed = [raw_dependency(node)
                        for node in children(management, "dependencies")]


def parse_pom(text):
    """Разбирает текст POM-файла."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as err:
        raise RepositoryError(f"некорректный POM: {err}") from None
    strip_namespaces(root)
    return Pom(root)


def interpolate(text, props):
    """Подставляет значения ${свойство}; неизвестные остаются как есть."""
    for _ in range(MAX_PASSES):
        new = VAR_RE.sub(lambda m: props.get(m.group(1), m.group(0)), text)
        if new == text:
            break
        text = new
    return text


def normalize_version(version):
    """Диапазон версий [1.0,2.0) заменяет его нижней границей."""
    if version and version[0] in RANGE_CHARS:
        return version.strip(RANGE_CHARS).split(",")[0].strip()
    return version


def collect_properties(poms):
    """Свойства цепочки POM; потомок переопределяет предков."""
    props = {}
    for pom in reversed(poms):
        props.update(pom.properties)
    first = poms[0]
    for prefix in ("project.", "pom.", ""):
        props[prefix + "groupId"] = first.group
        props[prefix + "version"] = first.version
    props["project.artifactId"] = first.artifact
    if first.parent:
        props["project.parent.version"] = first.parent.version
        props["parent.version"] = first.parent.version
    return props


def collect_managed(poms, props):
    """Версии из dependencyManagement: {(группа, артефакт): версия}."""
    managed = {}
    for pom in reversed(poms):
        for raw in pom.managed:
            key = (interpolate(raw["group"], props),
                   interpolate(raw["artifact"], props))
            managed[key] = interpolate(raw["version"], props)
    return managed


def is_included(raw):
    """Зависимость попадает в граф: scope compile/runtime, не optional."""
    scope = raw["scope"] or DEFAULT_SCOPE
    return scope in INCLUDED_SCOPES and raw["optional"] != "true"


class MavenRepository:
    """Репозиторий Maven, доступный по URL (или через функцию fetch)."""

    def __init__(self, url, fetch=fetch_text):
        """Запоминает адрес репозитория и функцию загрузки."""
        self.url = url.rstrip("/")
        self.fetch = fetch
        self.cache = {}
        self.warnings = []

    def pom_url(self, coord):
        """URL POM-файла по стандартной раскладке репозитория Maven."""
        folder = coord.group.replace(".", "/")
        name = f"{coord.artifact}-{coord.version}.pom"
        return f"{self.url}/{folder}/{coord.artifact}/{coord.version}/{name}"

    def load_pom(self, coord):
        """Загружает и разбирает POM (с кэшированием)."""
        key = str(coord)
        if key not in self.cache:
            self.cache[key] = parse_pom(self.fetch(self.pom_url(coord)))
        return self.cache[key]

    def chain(self, coord):
        """POM пакета и его родителей: от потомка к предку."""
        poms, seen, current = [], set(), coord
        while current is not None and str(current) not in seen:
            if len(poms) >= MAX_PARENT_DEPTH:
                raise RepositoryError("слишком длинная цепочка parent")
            seen.add(str(current))
            pom = self.load_pom(current)
            poms.append(pom)
            current = pom.parent
        return poms

    def resolve(self, raw, props, managed):
        """Строка группа:артефакт:версия или None, если пропущена."""
        if not is_included(raw):
            return None
        group = interpolate(raw["group"], props)
        artifact = interpolate(raw["artifact"], props)
        version = interpolate(raw["version"], props)
        version = version or managed.get((group, artifact), "")
        version = normalize_version(version)
        if not version or "${" in group + artifact + version:
            self.warnings.append(
                f"пропущена зависимость {group}:{artifact}: "
                f"версия не определена")
            return None
        return f"{group}:{artifact}:{version}"

    def dependencies(self, name):
        """Прямые зависимости пакета (compile и runtime, без optional)."""
        poms = self.chain(Coord.parse(name))
        props = collect_properties(poms)
        managed = collect_managed(poms, props)
        result = []
        for pom in poms:
            for raw in pom.dependencies:
                dep = self.resolve(raw, props, managed)
                if dep and dep not in result:
                    result.append(dep)
        return result
