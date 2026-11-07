"""Тесты тестового репозитория из файла."""
import unittest

from filerepo import FileRepository
from helpers import write_temp
from maven import RepositoryError


class FileRepositoryTest(unittest.TestCase):
    """Проверки чтения файла описания графа."""

    def repo(self, text):
        """Создаёт репозиторий из текста."""
        return FileRepository(write_temp(self, text, ".txt"))

    def test_dependencies(self):
        """Читаются зависимости, комментарии и пустые строки."""
        repo = self.repo("# c\n\nA: B C\nB: C\n")
        self.assertEqual(repo.dependencies("A"), ["B", "C"])
        self.assertEqual(repo.dependencies("C"), [])
        self.assertEqual(repo.packages(), ["A", "B", "C"])

    def test_commas_and_duplicates(self):
        """Допускаются запятые; повторы убираются."""
        repo = self.repo("A: B,C, B\n")
        self.assertEqual(repo.dependencies("A"), ["B", "C"])

    def test_multiletter_names(self):
        """Имена из нескольких заглавных букв допустимы."""
        self.assertEqual(self.repo("AB: CD\n").dependencies("AB"), ["CD"])

    def test_unknown_package(self):
        """Неизвестный пакет - RepositoryError."""
        with self.assertRaisesRegex(RepositoryError, "не найден"):
            self.repo("A:\n").dependencies("Z")

    def test_format_errors(self):
        """Строка без ':', строчные буквы, цифры, повтор описания."""
        for text, fragment in (("A B\n", "формат"),
                               ("a: B\n", "заглавных"),
                               ("A: b1\n", "заглавных"),
                               ("A: B\nA: C\n", "повторно")):
            with self.assertRaisesRegex(RepositoryError, fragment):
                self.repo(text)

    def test_missing_file(self):
        """Отсутствующий файл - RepositoryError."""
        with self.assertRaises(RepositoryError):
            FileRepository("no/such/graph.txt")
