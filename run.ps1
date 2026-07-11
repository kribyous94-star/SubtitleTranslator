# Lance SubtitleTranslator (serveur web local sur http://127.0.0.1:8765).
#
# Variables d'environnement optionnelles :
#   $env:HOST  — adresse d'écoute (défaut : 127.0.0.1)
#   $env:PORT  — port           (défaut : 8765)
$ErrorActionPreference = 'Stop'

$ROOT   = $PSScriptRoot
$APP_PY = Join-Path $ROOT "venvs\app\Scripts\python.exe"

if (-not (Test-Path $APP_PY)) {
    Write-Error "Le venv « app » est introuvable. Lancer d'abord : .\install.ps1"
    exit 1
}

$HOST_ADDR = if ($env:HOST) { $env:HOST } else { "127.0.0.1" }
$PORT_NUM  = if ($env:PORT) { $env:PORT } else { "8765" }

Write-Host "SubtitleTranslator : http://${HOST_ADDR}:${PORT_NUM}  (Ctrl+C pour arrêter)"
Set-Location $ROOT
& $APP_PY -m uvicorn app.main:app --host $HOST_ADDR --port $PORT_NUM
