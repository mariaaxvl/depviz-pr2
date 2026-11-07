"""Визуализатор графа зависимостей Maven-пакетов."""
import argparse
import os
import sys

from config import ConfigError, load_config
from filerepo import FileRepository
from graph import (GraphError, build_full_graph, build_graph, describe,
                   describe_reverse, reverse_graph)
from maven import MavenRepository, RepositoryError
from render import (RenderError, ascii_tree, plantuml_text, render_png,
                    save_file)

EXIT_OK = 0
EXIT_CONFIG = 2
EXIT_REPO = 3
EXIT_GRAPH = 4
EXIT_RENDER = 5


def parse_args(argv=None):
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов")
    parser.add_argument("config", help="путь к CSV-файлу конфигурации")
    parser.add_argument(
        "--no-image", action="store_true",
        help="не создавать PlantUML и PNG (только текстовый вывод)")
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


def save_images(config, graph):
    """Сохраняет диаграмму PlantUML и изображение PNG."""
    kind = "Обратные зависимости" if config.reverse else "Зависимости"
    text = plantuml_text(graph, config.package,
                         f"{kind}: {config.package}", config.reverse)
    puml_path = os.path.splitext(config.output)[0] + ".puml"
    save_file(puml_path, text.encode("utf-8"))
    print(f"PlantUML сохранён: {puml_path}")
    save_file(config.output, render_png(text))
    print(f"PNG сохранён: {config.output}")


def show_results(config, graph, no_image):
    """Печатает отчёт и ASCII-дерево, сохраняет изображения."""
    print(report(config, graph))
    if config.ascii_tree:
        print("ASCII-дерево:")
        print(ascii_tree(graph, config.package))
    if not no_image:
        save_images(config, graph)


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
    for warning in getattr(repo, "warnings", []):
        print(f"Предупреждение: {warning}", file=sys.stderr)
    try:
        show_results(config, graph, args.no_image)
    except RenderError as err:
        print(f"Ошибка визуализации: {err}", file=sys.stderr)
        return EXIT_RENDER
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
