"""Тестовый репозиторий: граф пакетов, описанный в текстовом файле."""
import re

from maven import RepositoryError

NAME_RE = re.compile(r"^[A-Z]+$")
LIST_SPLIT = re.compile(r"[,\s]+")
COMMENT = "#"
SEPARATOR = ":"
FIRST_LINE = 1


class FileRepository:
    """Читает строки вида 'A: B C' (пакет: его зависимости)."""

    def __init__(self, path):
        """Загружает файл с описанием графа."""
        self.path = path
        self.edges = {}
        self.names = set()
        self._load()

    def _load(self):
        """Читает все строки файла."""
        try:
            with open(self.path, encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as err:
            raise RepositoryError(
                f"не удалось прочитать {self.path}: {err}") from None
        for number, line in enumerate(lines, FIRST_LINE):
            self._parse_line(number, line)

    def _fail(self, number, message):
        """Ошибка формата файла с номером строки."""
        raise RepositoryError(f"{self.path}, строка {number}: {message}")

    def _check_name(self, number, name):
        """Имя пакета - заглавные латинские буквы."""
        if not NAME_RE.match(name):
            self._fail(number, f"имя '{name}' должно состоять из "
                               f"заглавных латинских букв")

    def _parse_line(self, number, line):
        """Разбирает одну строку описания."""
        text = line.strip()
        if not text or text.startswith(COMMENT):
            return
        name, separator, rest = text.partition(SEPARATOR)
        if not separator:
            self._fail(number, "ожидается формат 'ПАКЕТ: ЗАВИСИМОСТИ'")
        name = name.strip()
        deps = [item for item in LIST_SPLIT.split(rest.strip()) if item]
        for item in [name] + deps:
            self._check_name(number, item)
        if name in self.edges:
            self._fail(number, f"пакет '{name}' описан повторно")
        self.edges[name] = list(dict.fromkeys(deps))
        self.names.update([name] + deps)

    def packages(self):
        """Все пакеты репозитория в алфавитном порядке."""
        return sorted(self.names)

    def dependencies(self, name):
        """Прямые зависимости пакета."""
        if name not in self.names:
            raise RepositoryError(
                f"пакет '{name}' не найден в тестовом репозитории")
        return list(self.edges.get(name, []))
