"""Тесты чтения и проверки конфигурационного файла."""
import os
import unittest

from config import ConfigError, load_config
from helpers import DATA_DIR, write_temp

SIMPLE = os.path.join(DATA_DIR, "graphs", "simple.txt")
BASE = {
    "package": "com.example:app:1.0",
    "repo": "http://127.0.0.1:8765",
    "test_mode": "false",
    "output": "out/g.png",
    "ascii_tree": "false",
    "filter": "",
}


def make_csv(overrides=None, drop=()):
    """Текст CSV на основе BASE с заменами и пропуском ключей."""
    values = dict(BASE)
    values.update(overrides or {})
    rows = [f"{key},{val}" for key, val in values.items() if key not in drop]
    return "\n".join(rows) + "\n"


class ConfigTest(unittest.TestCase):
    """Проверки загрузки корректных конфигураций."""

    def load(self, text):
        """Загружает конфигурацию из текста."""
        return load_config(write_temp(self, text))

    def test_valid_maven(self):
        """Корректная конфигурация для Maven-репозитория."""
        config = self.load(make_csv())
        self.assertEqual(config.package, "com.example:app:1.0")
        self.assertFalse(config.test_mode)

    def test_valid_test_mode(self):
        """Корректная конфигурация тестового режима."""
        text = make_csv({"package": "A", "repo": SIMPLE,
                         "test_mode": "true", "ascii_tree": "yes"})
        config = self.load(text)
        self.assertTrue(config.test_mode and config.ascii_tree)

    def test_header_and_bom(self):
        """Заголовок key,value и BOM допускаются."""
        text = "\ufeffkey,value\n" + make_csv()
        self.assertEqual(self.load(text).output, "out/g.png")

    def test_quoted_filter(self):
        """Значение с запятой задаётся в кавычках."""
        config = self.load(make_csv({"filter": '"a,b"'}))
        self.assertEqual(config.substring, "a,b")

    def test_items_order(self):
        """items() возвращает все параметры."""
        keys = [key for key, _ in self.load(make_csv()).items()]
        self.assertEqual(keys[:len(BASE)], list(BASE))


class ConfigErrorTest(unittest.TestCase):
    """Проверки обработки ошибок для каждого параметра."""

    def fails(self, text, fragment):
        """Загрузка должна завершиться ConfigError с фрагментом текста."""
        path = write_temp(self, text)
        with self.assertRaisesRegex(ConfigError, fragment):
            load_config(path)

    def test_missing_file(self):
        """Файл конфигурации не найден."""
        with self.assertRaisesRegex(ConfigError, "не найден"):
            load_config("no/such/config.csv")

    def test_bad_row(self):
        """Строка не из двух полей."""
        self.fails(make_csv() + "oops\n", "два поля")

    def test_unknown_key(self):
        """Неизвестный параметр."""
        self.fails(make_csv() + "color,red\n", "неизвестный")

    def test_duplicate_key(self):
        """Повторно заданный параметр."""
        self.fails(make_csv() + "package,A\n", "повторно")

    def test_missing_key(self):
        """Не задан обязательный параметр."""
        self.fails(make_csv(drop=("output",)), "не заданы.*output")

    def test_bad_bool(self):
        """Неверное значение режима."""
        self.fails(make_csv({"test_mode": "maybe"}), "true или false")
        self.fails(make_csv({"ascii_tree": "2"}), "ascii_tree")

    def test_empty_package(self):
        """Пустое имя пакета."""
        self.fails(make_csv({"package": ""}), "не задано")

    def test_bad_maven_name(self):
        """Имя Maven-пакета не в формате g:a:v."""
        self.fails(make_csv({"package": "guava"}), "группа:артефакт")

    def test_bad_test_name(self):
        """В тестовом режиме имя - заглавные латинские буквы."""
        text = make_csv({"package": "a1", "repo": SIMPLE,
                         "test_mode": "true"})
        self.fails(text, "заглавные")

    def test_bad_url(self):
        """Неверный URL репозитория."""
        self.fails(make_csv({"repo": "ftp://x"}), "URL")
        self.fails(make_csv({"repo": ""}), "не задано")

    def test_missing_graph_file(self):
        """Файл тестового репозитория не существует."""
        text = make_csv({"package": "A", "repo": "no/file.txt",
                         "test_mode": "true"})
        self.fails(text, "не найден")

    def test_bad_output(self):
        """Неверное имя файла изображения."""
        self.fails(make_csv({"output": "graph.jpg"}), "png")
        self.fails(make_csv({"output": ".png"}), "png")
        self.fails(make_csv({"output": "a?b.png"}), "недопустимые")
        self.fails(make_csv({"output": ""}), "не задано")


class ReverseConfigTest(unittest.TestCase):
    """Параметры режима обратных зависимостей."""

    def load(self, **overrides):
        """Загружает конфигурацию BASE с заменами."""
        return load_config(write_temp(self, make_csv(overrides)))

    def test_default_off(self):
        """По умолчанию режим выключен."""
        config = self.load()
        self.assertFalse(config.reverse)
        self.assertEqual(config.universe, [])

    def test_universe(self):
        """Список корней разделяется точкой с запятой."""
        config = self.load(reverse="true",
                           universe="a:b:1; c:d:2")
        self.assertEqual(config.universe, ["a:b:1", "c:d:2"])

    def test_universe_required(self):
        """Для Maven reverse без universe - ошибка."""
        with self.assertRaisesRegex(ConfigError, "universe"):
            self.load(reverse="true")

    def test_bad_universe_item(self):
        """Неверное имя в universe."""
        with self.assertRaisesRegex(ConfigError, "universe"):
            self.load(universe="guava")

    def test_bad_reverse(self):
        """Неверное значение reverse."""
        with self.assertRaisesRegex(ConfigError, "reverse"):
            self.load(reverse="2")

    def test_test_mode_needs_no_universe(self):
        """В тестовом режиме universe не нужен."""
        config = self.load(package="A", repo=SIMPLE, test_mode="true",
                           reverse="true")
        self.assertTrue(config.reverse)
