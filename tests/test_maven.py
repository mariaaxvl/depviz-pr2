"""Тесты получения зависимостей из POM-файлов Maven."""
import functools
import os
import unittest

from helpers import DATA_DIR, start_repo_server
from maven import (Coord, MavenRepository, RepositoryError, fetch_text,
                   normalize_version)

REPO_DIR = os.path.join(DATA_DIR, "maven_repo")
BASE_URL = "http://repo.test"
APP = "com.example:app:1.0"


def local_fetch(url):
    """Имитация загрузки: читает POM из тестового каталога."""
    path = os.path.join(REPO_DIR, *url[len(BASE_URL) + 1:].split("/"))
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except FileNotFoundError:
        raise RepositoryError(f"не найден в репозитории: {url}") from None


class DependenciesTest(unittest.TestCase):
    """Проверки разбора POM и разрешения версий."""

    @functools.cached_property
    def repo(self):
        """Репозиторий поверх тестовых файлов (свой для каждого теста)."""
        return MavenRepository(BASE_URL, local_fetch)

    def test_direct_dependencies(self):
        """Версии берутся из свойств parent и dependencyManagement."""
        self.assertEqual(self.repo.dependencies(APP), [
            "com.example:lib-a:1.0",
            "com.example:lib-b:2.0",
            "com.example:managed:3.0",
        ])

    def test_scopes_and_optional_skipped(self):
        """test, provided и optional зависимости не учитываются."""
        text = " ".join(self.repo.dependencies(APP))
        for name in ("junit", "opt", "prov"):
            self.assertNotIn(name, text)

    def test_unresolved_version_warning(self):
        """Зависимость без версии пропускается с предупреждением."""
        self.repo.dependencies(APP)
        self.assertEqual(len(self.repo.warnings), 1)
        self.assertIn("ghost", self.repo.warnings[0])

    def test_group_with_dots(self):
        """Точки в имени группы превращаются в каталоги."""
        self.assertEqual(self.repo.dependencies("com.example:lib-c:1.0"),
                         ["org.demo:util:1.0"])

    def test_no_dependencies(self):
        """Пакет без зависимостей даёт пустой список."""
        self.assertEqual(
            self.repo.dependencies("com.example:managed:3.0"), [])

    def test_pom_cached(self):
        """Повторный запрос не загружает POM заново."""
        calls = []
        repo = MavenRepository(BASE_URL, lambda u: calls.append(u)
                               or local_fetch(u))
        repo.dependencies(APP)
        count = len(calls)
        repo.dependencies(APP)
        self.assertEqual(len(calls), count)

    def test_unknown_package(self):
        """Отсутствующий пакет - RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            self.repo.dependencies("com.example:nope:1.0")

    def test_broken_pom(self):
        """Некорректный XML - RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "некорректный POM"):
            self.repo.dependencies("com.example:broken:1.0")

    def test_bad_coordinates(self):
        """Неверные координаты пакета."""
        for text in ("a:b", "a::1", "a:b:c:d"):
            with self.assertRaises(RepositoryError):
                Coord.parse(text)

    def test_version_range(self):
        """Диапазон версий заменяется нижней границей."""
        self.assertEqual(normalize_version("[1.2,2.0)"), "1.2")
        self.assertEqual(normalize_version("[1.5]"), "1.5")
        self.assertEqual(normalize_version("(,1.0]"), "")
        self.assertEqual(normalize_version("2.1"), "2.1")


class FetchTest(unittest.TestCase):
    """Проверки загрузки по HTTP с локальным сервером."""

    def test_fetch_ok(self):
        """Файл скачивается по HTTP."""
        url = start_repo_server(self, REPO_DIR)
        repo = MavenRepository(url)
        self.assertEqual(len(repo.dependencies(APP)), 3)

    def test_fetch_404(self):
        """Ответ 404 - понятная ошибка."""
        url = start_repo_server(self, REPO_DIR)
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            fetch_text(url + "/missing.pom")

    def test_unreachable(self):
        """Недоступный сервер - RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "недоступен"):
            fetch_text("http://127.0.0.1:1/x.pom")
