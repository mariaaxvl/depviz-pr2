#!/usr/bin/env bash
# Этап 3: граф зависимостей (DFS), циклы, фильтр, тестовый репозиторий.
source "$(dirname "$0")/lib.sh"

echo "##### Тестовый репозиторий: разные случаи #####"
try_graph "ромб: общая зависимость" simple A ""
try_graph "большой граф с общими зависимостями" multi A ""
try_graph "подграф: корень B" multi B ""
try_graph "пакет без зависимостей" single A ""

echo "##### Циклические зависимости #####"
try_graph "цикл через корень" cycle A ""
try_graph "цикл не через корень" cycle_inner A ""
try_graph "зависимость от самого себя" selfloop A ""

echo "##### Фильтр по подстроке #####"
try_graph "исключить E" multi A "E"
try_graph "исключить F" multi A "F"
try_graph "исключить B" simple A "B"

echo "##### Maven-репозиторий (локальный HTTP) #####"
start_server
trap stop_server EXIT
run_config tests/data/configs/maven.csv
try_edit "Maven: цикл cyc-x <-> cyc-y" \
    's/^package,.*/package,com.example:root:1.0/'
try_edit "Maven: фильтр lib-c" 's/^filter,.*/filter,lib-c/'

echo "##### Ошибки #####"
try_graph "пакета нет в репозитории" simple Z ""
try_graph "корневой пакет исключён фильтром" simple A "A"
try_bad_graph "файл графа: нет двоеточия" "A B"
try_bad_graph "файл графа: имя строчными" "a: B"
try_bad_graph "файл графа: пакет описан дважды" "A: B" "A: C"
