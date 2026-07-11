# Installe SubtitleTranslator : crée les venvs dans .\venvs et installe les
# dépendances. Tout reste dans ce dossier — le supprimer supprime tout.
#
# Usage : .\install.ps1 [-NoHF] [-NoArgos]
#   -NoHF     : ne pas installer le backend Hugging Face (NLLB/M2M100, le plus lourd)
#   -NoArgos  : ne pas installer le backend Argos Translate
#
# Pré-requis : Python >= 3.10 dans le PATH (ou variable $env:PYTHON).
param(
    [switch]$NoHF,
    [switch]$NoArgos
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ROOT   = $PSScriptRoot
$PYTHON = if ($env:PYTHON) { $env:PYTHON } else { "python" }

# ── Vérification Python ≥ 3.10 ─────────────────────────────────────────────
& $PYTHON -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
if ($LASTEXITCODE -ne 0) {
    $ver = (& $PYTHON --version 2>&1) -join ''
    Write-Error "Erreur : Python >= 3.10 requis (trouvé : $ver)."
    exit 1
}

# ── Vérification du module venv ─────────────────────────────────────────────
& $PYTHON -m venv --help 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Erreur : le module venv est indisponible. Réinstallez Python en cochant 'tcl/tk and IDLE'."
    exit 1
}

# ── Fonction : créer/mettre à jour un venv ──────────────────────────────────
function Invoke-MakeVenv {
    param(
        [string]   $Name,
        [string]   $Req,
        [string[]] $ExtraArgs = @()
    )
    $venv      = Join-Path $ROOT "venvs\$Name"
    $pythonExe = Join-Path $venv "Scripts\python.exe"

    Write-Host ""
    Write-Host "==> venv « $Name »"

    if (-not (Test-Path $pythonExe)) {
        & $PYTHON -m venv $venv
        if ($LASTEXITCODE -ne 0) { throw "Échec de la création du venv « $Name »." }
    }

    & $pythonExe -m pip install --quiet --upgrade pip
    if ($LASTEXITCODE -ne 0) { throw "Échec de la mise à jour de pip dans « $Name »." }

    & $pythonExe -m pip install -r $Req @ExtraArgs
    if ($LASTEXITCODE -ne 0) { throw "Échec de pip install pour le venv « $Name »." }

    Write-Host "    OK : $venv"
}

# ── Installation ─────────────────────────────────────────────────────────────
Write-Host "Installation de SubtitleTranslator dans : $ROOT"

Invoke-MakeVenv -Name "app" -Req "$ROOT\app\requirements.txt"

if (-not $NoArgos) {
    # argostranslate dépend de stanza -> torch : forcer torch CPU
    Invoke-MakeVenv -Name "argos" `
        -Req "$ROOT\backends\argos\requirements.txt" `
        -ExtraArgs @('--extra-index-url', 'https://download.pytorch.org/whl/cpu')
} else {
    Write-Host ""; Write-Host "==> backend argos ignoré (-NoArgos)"
}

if (-not $NoHF) {
    # torch CPU uniquement : évite les ~2 Go de bibliothèques CUDA
    Invoke-MakeVenv -Name "hf" `
        -Req "$ROOT\backends\hf\requirements.txt" `
        -ExtraArgs @('--extra-index-url', 'https://download.pytorch.org/whl/cpu')
} else {
    Write-Host ""; Write-Host "==> backend hf ignoré (-NoHF)"
}

# ── Dossiers de données ──────────────────────────────────────────────────────
foreach ($dir in @(
    "$ROOT\models\argos\packages",
    "$ROOT\models\hf",
    "$ROOT\models\cache",
    "$ROOT\data\jobs"
)) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

Write-Host ""
Write-Host "Installation terminée."
Write-Host "  1. Lancer :  .\run.ps1   (ou double-clic sur run.bat)"
Write-Host "  2. Ouvrir :  http://127.0.0.1:8765"
Write-Host "  3. Onglet « Modèles » pour télécharger les modèles de traduction"
Write-Host "     (internet requis une seule fois, tout fonctionne ensuite hors ligne)."
