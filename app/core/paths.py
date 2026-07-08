"""Chemins du projet. Tout vit sous la racine du dossier : supprimer le
dossier supprime venvs, modèles et données."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

VENVS = ROOT / "venvs"
BACKENDS = ROOT / "backends"
MODELS = ROOT / "models"
DATA = ROOT / "data"

ARGOS_PACKAGES = MODELS / "argos" / "packages"
HF_HOME = MODELS / "hf"
CACHE = MODELS / "cache"
XDG_DATA = MODELS / "xdg"

JOBS_DIR = DATA / "jobs"
CONFIG_FILE = DATA / "config.json"

STATIC = ROOT / "app" / "static"


def ensure_dirs() -> None:
    for p in (ARGOS_PACKAGES, HF_HOME, CACHE, XDG_DATA, JOBS_DIR):
        p.mkdir(parents=True, exist_ok=True)
