#!/usr/bin/env bash
# Installe SubtitleTranslator : crée les venvs dans ./venvs et installe les
# dépendances. Tout reste dans ce dossier — le supprimer supprime tout.
#
# Usage : ./install.sh [--no-hf] [--no-argos]
#   --no-hf     ne pas installer le backend Hugging Face (NLLB/M2M100, le plus lourd)
#   --no-argos  ne pas installer le backend Argos Translate
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"

INSTALL_HF=1
INSTALL_ARGOS=1
for arg in "$@"; do
    case "$arg" in
        --no-hf)    INSTALL_HF=0 ;;
        --no-argos) INSTALL_ARGOS=0 ;;
        *) echo "Option inconnue : $arg" >&2; exit 1 ;;
    esac
done

if ! "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    echo "Erreur : Python >= 3.10 requis (trouvé : $($PYTHON --version 2>&1 || echo 'aucun'))." >&2
    exit 1
fi
if ! "$PYTHON" -m venv --help >/dev/null 2>&1; then
    echo "Erreur : le module venv est indisponible (sur Debian/Ubuntu : sudo apt install python3-venv)." >&2
    exit 1
fi

make_venv() {  # make_venv <nom> <requirements> [pip args supplémentaires...]
    local name="$1" req="$2"; shift 2
    local venv="$ROOT/venvs/$name"
    echo ""
    echo "==> venv « $name »"
    if [ ! -x "$venv/bin/python" ]; then
        "$PYTHON" -m venv "$venv"
    fi
    "$venv/bin/python" -m pip install --quiet --upgrade pip
    "$venv/bin/python" -m pip install "$@" -r "$req"
    echo "    OK : $venv"
}

echo "Installation de SubtitleTranslator dans : $ROOT"

make_venv app "$ROOT/app/requirements.txt"

if [ "$INSTALL_ARGOS" = 1 ]; then
    make_venv argos "$ROOT/backends/argos/requirements.txt"
else
    echo ""; echo "==> backend argos ignoré (--no-argos)"
fi

if [ "$INSTALL_HF" = 1 ]; then
    # torch CPU uniquement (index PyTorch) : évite les ~2 Go de bibliothèques CUDA
    make_venv hf "$ROOT/backends/hf/requirements.txt" \
        --extra-index-url https://download.pytorch.org/whl/cpu
else
    echo ""; echo "==> backend hf ignoré (--no-hf)"
fi

mkdir -p "$ROOT/models/argos/packages" "$ROOT/models/hf" "$ROOT/models/cache" "$ROOT/data/jobs"

echo ""
echo "Installation terminée."
echo "  1. Lancer :  ./run.sh"
echo "  2. Ouvrir :  http://127.0.0.1:8765"
echo "  3. Onglet « Modèles » pour télécharger les modèles de traduction"
echo "     (internet requis une seule fois, tout fonctionne ensuite hors ligne)."
