"""Визуализатор графа зависимостей (этап 1: конфигурация)."""
import argparse
import sys

from config import ConfigError, load_config

EXIT_OK = 0
EXIT_CONFIG = 2


def parse_args(argv=None):
    """Разбирает параметры командной строки."""
    parser = argparse.ArgumentParser(
        description="Визуализатор графа зависимостей пакетов")
    parser.add_argument("config", help="путь к CSV-файлу конфигурации")
    return parser.parse_args(argv)


def print_params(config):
    """Выводит все параметры пользователя в формате ключ = значение."""
    for key, value in config.items():
        print(f"{key} = {value}")


def configure_output():
    """Включает UTF-8 для вывода (Windows-консоли и каналы)."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def main(argv=None):
    """Точка входа; возвращает код завершения."""
    configure_output()
    args = parse_args(argv)
    try:
        config = load_config(args.config)
    except ConfigError as err:
        print(f"Ошибка конфигурации: {err}", file=sys.stderr)
        return EXIT_CONFIG
    print_params(config)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
