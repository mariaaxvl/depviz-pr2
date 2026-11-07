"""Визуализатор графа зависимостей (этап 2: сбор данных)."""
import argparse
import sys

from config import ConfigError, load_config
from maven import MavenRepository, RepositoryError

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_REPO = 3


def parse_args(argv=None):
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов")
    parser.add_argument("config", help="путь к CSV-файлу конфигурации")
    return parser.parse_args(argv)


def configure_output():
    """Включает UTF-8 для вывода (Windows-консоли и каналы)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def load_repository(config):
    """Создаёт репозиторий по настройкам."""
    if config.test_mode:
        raise RepositoryError("тестовый режим будет добавлен на этапе 3")
    return MavenRepository(config.repo)


def print_dependencies(package, dependencies):
    """Выводит прямые зависимости пакета."""
    print(f"Прямые зависимости пакета {package}:")
    for dep in dependencies:
        print(f"  {dep}")
    if not dependencies:
        print("  (нет прямых зависимостей)")


def main(argv=None):
    """Точка входа; возвращает код завершения."""
    configure_output()
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as err:
        print(f"Ошибка конфигурации: {err}", file=sys.stderr)
        return EXIT_CONFIG
    try:
        repo = load_repository(config)
        dependencies = repo.dependencies(config.package)
    except RepositoryError as err:
        print(f"Ошибка репозитория: {err}", file=sys.stderr)
        return EXIT_REPO
    print_dependencies(config.package, dependencies)
    for warning in repo.warnings:
        print(f"Предупреждение: {warning}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
