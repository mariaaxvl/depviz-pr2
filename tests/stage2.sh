#!/usr/bin/env bash
# Этап 2: прямые зависимости Maven-пакета (локальный HTTP-репозиторий).
# Реальный Maven Central (нужен интернет): CENTRAL=1 ./tests/stage2.sh
source "$(dirname "$0")/lib.sh"
start_server
trap stop_server EXIT

echo "##### Прямые зависимости #####"
run_config tests/data/configs/maven.csv
try_edit "пакет без зависимостей" 's/^package,.*/package,com.example:managed:3.0/'
try_edit "группа с точками в имени" 's/^package,.*/package,com.example:lib-c:1.0/'
try_edit "пакет с несколькими зависимостями" 's/^package,.*/package,com.example:lib-b:2.0/'

echo "##### Ошибки получения данных #####"
try_edit "пакет не найден (404)" 's/^package,.*/package,com.example:nope:1.0/'
try_edit "некорректный POM" 's/^package,.*/package,com.example:broken:1.0/'
try_edit "репозиторий недоступен" 's#^repo,.*#repo,http://127.0.0.1:1#'

if [ -n "$CENTRAL" ]; then
    echo "##### Maven Central #####"
    run_config tests/data/configs/central.csv
fi
