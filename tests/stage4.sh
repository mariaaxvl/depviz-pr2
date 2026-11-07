#!/usr/bin/env bash
# Этап 4: обратные зависимости (кто зависит от заданного пакета).
source "$(dirname "$0")/lib.sh"

echo "##### Тестовый репозиторий #####"
try_reverse "ромб: кто зависит от D" simple D ""
try_reverse "кто зависит от B" simple B ""
try_reverse "корень: от A никто не зависит" simple A ""
try_reverse "большой граф: кто зависит от G" multi G ""
try_reverse "большой граф: кто зависит от F" multi F ""
try_reverse "единственный пакет" single A ""
try_reverse "цикл: обратные зависимости A" cycle A ""
try_reverse "цикл не через корень: кто зависит от D" cycle_inner D ""
try_reverse "фильтр F: кто зависит от G" multi G "F"

echo "##### Maven-репозиторий (локальный HTTP) #####"
start_server
trap stop_server EXIT
try_maven_reverse "Maven: кто зависит от lib-c" com.example:lib-c:1.0 \
    "com.example:root:1.0"
try_maven_reverse "Maven: кто зависит от util (два корня)" \
    org.demo:util:1.0 "com.example:app:1.0;com.example:cyc-x:1.0"
try_maven_reverse "Maven: цикл cyc-x" com.example:cyc-x:1.0 \
    "com.example:root:1.0"

echo "##### Ошибки #####"
try_reverse "пакета нет в графе" simple Z ""
try_reverse "пакет исключён фильтром" simple D "D"
try_edit "Maven: reverse без universe" '$a reverse,true'
try_edit "reverse: не bool" '$a reverse,maybe'
try_edit "universe: неверное имя" '$a reverse,true\nuniverse,guava'
try_maven_reverse "Maven: пакета нет в universe" com.example:nope:1.0 \
    "com.example:app:1.0"
