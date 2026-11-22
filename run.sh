#!/usr/bin/env sh
# Start Prompt Coach on macOS or Linux:  ./run.sh
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 launch.py "$@"
elif command -v python >/dev/null 2>&1; then
    exec python launch.py "$@"
else
    echo "Python 3.10 or newer is required. Download it from https://www.python.org/downloads/"
    exit 1
fi
