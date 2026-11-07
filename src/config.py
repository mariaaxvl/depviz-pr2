"""Чтение и проверка конфигурационного файла в формате CSV."""
import csv
import os
import re
from dataclasses import dataclass, field

REQUIRED_KEYS = (
    "package", "repo", "test_mode", "output", "ascii_tree", "filter",
)
OPTIONAL_KEYS = ("reverse", "universe")
ALL_KEYS = REQUIRED_KEYS + OPTIONAL_KEYS
UNIVERSE_SEPARATOR = ";"
HEADER = ("key", "value")
COLUMNS = 2
FIRST_LINE = 1
TRUE_VALUES = ("true", "yes", "1")
FALSE_VALUES = ("false", "no", "0")
MAVEN_RE = re.compile(r"^[\w.\-]+:[\w.\-]+:[\w.\-]+$")
TEST_NAME_RE = re.compile(r"^[A-Z]+$")
URL_RE = re.compile(r"^https?://[A-Za-z0-9.\-]+(:\d+)?(/\S*)?$")
PNG_SUFFIX = ".png"
BAD_NAME_CHARS = '<>:"|?*'


class ConfigError(Exception):
    """Ошибка в конфигурационном файле или в значении параметра."""


@dataclass
class Config:
    """Параметры, заданные пользователем."""

    package: str
    repo: str
    test_mode: bool
    output: str
    ascii_tree: bool
    substring: str
    reverse: bool = False
    universe: list = field(default_factory=list)

    def items(self):
        """Пары (ключ, значение) в порядке конфигурационного файла."""
        return [
            ("package", self.package),
            ("repo", self.repo),
            ("test_mode", str(self.test_mode).lower()),
            ("output", self.output),
            ("ascii_tree", str(self.ascii_tree).lower()),
            ("filter", self.substring),
            ("reverse", str(self.reverse).lower()),
            ("universe", UNIVERSE_SEPARATOR.join(self.universe)),
        ]


def add_pair(pairs, key, value, number):
    """Добавляет пару в словарь, проверяя имя и повторы ключа."""
    if key not in ALL_KEYS:
        raise ConfigError(f"строка {number}: неизвестный параметр '{key}'")
    if key in pairs:
        raise ConfigError(f"строка {number}: параметр '{key}' задан повторно")
    pairs[key] = value


def rows_to_pairs(rows):
    """Преобразует строки CSV в словарь параметров."""
    pairs = {}
    for number, row in enumerate(rows, FIRST_LINE):
        if not any(cell.strip() for cell in row):
            continue
        if len(row) != COLUMNS:
            raise ConfigError(
                f"строка {number}: ожидаются два поля 'ключ,значение'")
        key, value = row[0].strip(), row[1].strip()
        if number == FIRST_LINE and (key, value) == HEADER:
            continue
        add_pair(pairs, key, value, number)
    return pairs


def read_pairs(path):
    """Читает CSV-файл и возвращает словарь параметров."""
    try:
        with open(path, encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
    except FileNotFoundError:
        raise ConfigError(f"файл конфигурации не найден: {path}") from None
    except (OSError, UnicodeDecodeError, csv.Error) as err:
        raise ConfigError(f"не удалось прочитать {path}: {err}") from None
    return rows_to_pairs(rows)


def check_required(pairs):
    """Все обязательные параметры должны быть заданы."""
    missing = [key for key in REQUIRED_KEYS if key not in pairs]
    if missing:
        raise ConfigError("не заданы параметры: " + ", ".join(missing))


def parse_bool(key, text):
    """Преобразует true/false (yes/no, 1/0) в bool."""
    value = text.lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ConfigError(
        f"параметр '{key}': ожидается true или false, получено '{text}'")


def check_package(value, test_mode):
    """Имя пакета: группа:артефакт:версия или заглавные латинские буквы."""
    if not value:
        raise ConfigError("параметр 'package': имя пакета не задано")
    if test_mode:
        pattern, hint = TEST_NAME_RE, "заглавные латинские буквы, например A"
    else:
        pattern, hint = MAVEN_RE, "формат группа:артефакт:версия"
    if not pattern.match(value):
        raise ConfigError(
            f"параметр 'package': неверное имя '{value}' ({hint})")


def check_repo(value, test_mode):
    """URL репозитория или путь к файлу тестового репозитория."""
    if not value:
        raise ConfigError("параметр 'repo': значение не задано")
    if test_mode:
        if not os.path.isfile(value):
            raise ConfigError(
                f"параметр 'repo': файл тестового репозитория не найден: "
                f"{value}")
    elif not URL_RE.match(value):
        raise ConfigError(
            f"параметр 'repo': ожидается URL http:// или https://, "
            f"получено '{value}'")


def check_output(value):
    """Имя файла изображения: непустое, с расширением .png."""
    if not value:
        raise ConfigError("параметр 'output': имя файла не задано")
    name = os.path.basename(value.replace("\\", "/"))
    if not name.lower().endswith(PNG_SUFFIX) or name.lower() == PNG_SUFFIX:
        raise ConfigError(
            f"параметр 'output': нужно имя файла с расширением .png, "
            f"получено '{value}'")
    if any(char in name for char in BAD_NAME_CHARS):
        raise ConfigError(
            f"параметр 'output': недопустимые символы в имени '{name}'")


def parse_universe(text):
    """Список Maven-пакетов, разделённых ';' (корни анализируемого набора)."""
    items = [part.strip() for part in text.split(UNIVERSE_SEPARATOR)]
    items = [part for part in items if part]
    for item in items:
        if not MAVEN_RE.match(item):
            raise ConfigError(
                f"параметр 'universe': неверное имя '{item}' "
                f"(формат группа:артефакт:версия)")
    return items


def check_reverse(reverse, test_mode, universe):
    """Для Maven режим reverse требует список пакетов universe."""
    if reverse and not test_mode and not universe:
        raise ConfigError(
            "параметр 'universe': для reverse в Maven нужен список "
            "пакетов через ';' (индекса обратных зависимостей нет)")


def load_config(path):
    """Читает и проверяет конфигурацию; возвращает Config."""
    pairs = read_pairs(path)
    check_required(pairs)
    test_mode = parse_bool("test_mode", pairs["test_mode"])
    ascii_tree = parse_bool("ascii_tree", pairs["ascii_tree"])
    check_package(pairs["package"], test_mode)
    check_repo(pairs["repo"], test_mode)
    check_output(pairs["output"])
    reverse = parse_bool("reverse", pairs.get("reverse", "false"))
    universe = parse_universe(pairs.get("universe", ""))
    check_reverse(reverse, test_mode, universe)
    return Config(pairs["package"], pairs["repo"], test_mode,
                  pairs["output"], ascii_tree, pairs["filter"],
                  reverse, universe)
