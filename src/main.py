"""Визуализатор графа зависимостей (этап 4: обратные зависимости)."""
import argparse
import sys

from config import ConfigError, load_config
from filerepo import FileRepository
from graph import (GraphError, build_full_graph, build_graph, describe,
                   describe_reverse, reverse_graph)
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


def analyze(config, repo):
    """Строит граф зависимостей или граф обратных зависимостей."""
    if not config.reverse:
        return build_graph(repo, config.package, config.substring)
    roots = repo.packages() if config.test_mode else config.universe
    full = build_full_graph(repo, roots, config.substring)
    return reverse_graph(full, config.package)


def report(config, graph):
    """Текстовый отчёт для выбранного режима."""
    if config.reverse:
        return describe_reverse(graph, config.package)
    return describe(graph, config.package)


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
        graph = analyze(config, repo)
    except RepositoryError as err:
        print(f"Ошибка репозитория: {err}", file=sys.stderr)
        return EXIT_REPO
    except GraphError as err:
        print(f"Ошибка графа: {err}", file=sys.stderr)
        return EXIT_GRAPH
    print(report(config, graph))
    for warning in getattr(repo, "warnings", []):
        print(f"Предупреждение: {warning}", file=sys.stderr)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
