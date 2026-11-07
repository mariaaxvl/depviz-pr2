"""Визуализатор графа зависимостей (этап 3: построение графа)."""
import argparse
import sys

from config import ConfigError, load_config
from filerepo import FileRepository
from graph import GraphError, build_graph, describe
from maven import MavenRepository, RepositoryError

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_REPO = 3
EXIT_GRAPH = 4


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
        return FileRepository(config.repo)
    return MavenRepository(config.repo)


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
        graph = build_graph(repo, config.package, config.substring)
    except RepositoryError as err:
        print(f"Ошибка репозитория: {err}", file=sys.stderr)
        return EXIT_REPO
    except GraphError as err:
        print(f"Ошибка графа: {err}", file=sys.stderr)
        return EXIT_GRAPH
    print(describe(graph, config.package))
    for warning in getattr(repo, "warnings", []):
        print(f"Предупреждение: {warning}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
