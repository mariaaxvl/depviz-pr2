#!/usr/bin/env bash
# Этап 5: PlantUML, PNG и ASCII-дерево для трёх разных пакетов.
# PNG: локальный plantuml (если установлен) или сервер plantuml.com
# (нужен интернет). Реальный Maven Central: CENTRAL=1 ./tests/stage5.sh
source "$(dirname "$0")/lib.sh"
EMU=("${EMU_FULL[@]}")
start_server
trap stop_server EXIT

echo "##### Пакет 1: A из большого тестового графа #####"
run_config tests/data/configs/demo_multi.csv
echo "##### Пакет 2: A, граф с циклом B -> D -> B #####"
run_config tests/data/configs/demo_cycle.csv
echo "##### Пакет 3: Maven app (локальный репозиторий) #####"
run_config tests/data/configs/demo_maven.csv
echo "##### Maven root: цикл cyc-x <-> cyc-y, фильтр lib-c #####"
run_config tests/data/configs/demo_maven_cycle.csv
echo "##### Обратные зависимости пакета G #####"
run_config tests/data/configs/demo_reverse.csv

echo "##### Текст PlantUML (out/demo_multi.puml) #####"
cat out/demo_multi.puml
echo "##### Созданные файлы #####"
ls -l out

if [ -n "$CENTRAL" ]; then
    echo "##### Maven Central #####"
    run_config tests/data/configs/central.csv
    run_config tests/data/configs/central_jackson.csv
    run_config tests/data/configs/central_text.csv
fi
