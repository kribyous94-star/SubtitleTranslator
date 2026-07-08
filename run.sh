#!/usr/bin/env bash
# Lance SubtitleTranslator (serveur web local sur http://127.0.0.1:8765).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PY="$ROOT/venvs/app/bin/python"

if [ ! -x "$APP_PY" ]; then
    echo "Le venv « app » est introuvable. Lancer d'abord : ./install.sh" >&2
    exit 1
fi

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

echo "SubtitleTranslator : http://$HOST:$PORT  (Ctrl+C pour arrêter)"
cd "$ROOT"
exec "$APP_PY" -m uvicorn app.main:app --host "$HOST" --port "$PORT"
