#!/usr/bin/env bash
# Этап 1: обработка ошибок для каждого параметра.
# Вывод параметров ключ=значение был только на этапе 1 (см. его коммит).
source "$(dirname "$0")/lib.sh"

echo "##### Ошибки командной строки и файла #####"
echo "== без аргументов =="; "${EMU[@]}"; echo "-- код возврата: $?"
run_config no_such_config.csv
try_text "строка не из двух полей" "package,A" "oops"
try_text "неизвестный параметр" "color,red"
try_edit "повторный параметр" '$a package,A'
try_edit "не задан параметр" '/^output,/d'

echo "##### Ошибки параметров #####"
try_edit "package: пусто" 's/^package,.*/package,/'
try_edit "package: не формат g:a:v" 's/^package,.*/package,guava/'
try_edit "repo: не URL" 's#^repo,.*#repo,ftp://example.org#'
try_edit "repo: пусто" 's#^repo,.*#repo,#'
try_edit "test_mode: не bool" 's/^test_mode,.*/test_mode,maybe/'
try_edit "test_mode: нет файла" \
    's/^test_mode,.*/test_mode,true/;s/^package,.*/package,A/;s#^repo,.*#repo,no/file.txt#'
try_edit "test_mode: имя не заглавными" \
    's/^test_mode,.*/test_mode,true/;s/^package,.*/package,a1/;s#^repo,.*#repo,tests/data/graphs/simple.txt#'
try_edit "output: не .png" 's/^output,.*/output,graph.jpg/'
try_edit "output: плохие символы" 's/^output,.*/output,a?b.png/'
try_edit "ascii_tree: не bool" 's/^ascii_tree,.*/ascii_tree,2/'
