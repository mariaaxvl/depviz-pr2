#!/usr/bin/env bash
# Общие функции тестовых скриптов (подключается командой source).
cd "$(dirname "${BASH_SOURCE[0]}")/.." || exit 1
PY="$(command -v python || command -v python3)"
EMU=("$PY" src/main.py)
TMP_CONFIG="tests/_tmp_config.csv"

base_config() {
    printf '%s\n' "package,com.example:app:1.0" \
        "repo,http://127.0.0.1:8765" "test_mode,false" \
        "output,out/g.png" "ascii_tree,false" "filter,"
}

run_config() {
    echo "-- запуск: ${EMU[*]} $1"
    "${EMU[@]}" "$1"
    echo "-- код возврата: $?"
}

try_edit() {
    echo "== $1 =="
    base_config | sed "$2" > "$TMP_CONFIG"
    run_config "$TMP_CONFIG"
    rm -f "$TMP_CONFIG"
}

try_text() {
    echo "== $1 =="
    printf '%s\n' "${@:2}" > "$TMP_CONFIG"
    run_config "$TMP_CONFIG"
    rm -f "$TMP_CONFIG"
}

start_server() {
    "$PY" -m http.server 8765 --bind 127.0.0.1 \
        --directory tests/data/maven_repo >/dev/null 2>&1 &
    SERVER_PID=$!
    sleep 1
}

stop_server() {
    kill "$SERVER_PID" 2>/dev/null
}
