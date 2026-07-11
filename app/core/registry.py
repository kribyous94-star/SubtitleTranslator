"""Catalogue des modèles de traduction et état installé/non installé.

L'état est déduit du contenu de models/ (aucune base de données) :
- hf    : présence du dossier models--<org>--<nom> dans models/hf/hub
- argos : lecture des metadata.json des paquets dans models/argos/packages
- api   : toujours « disponible » (rien à installer, en ligne)
"""
import json
import shutil

from .paths import ARGOS_PACKAGES, HF_HOME

CATALOG = {
    "argos": {
        "backend": "argos",
        "label": "Argos Translate",
        "description": "Petits modèles par paire de langues (~100 Mo). Rapide sur CPU.",
        "size": "~100 Mo / paire",
        "offline": True,
        "kind": "pairs",  # on installe des paires, pas le modèle entier
    },
    "nllb-200-distilled-600M": {
        "backend": "hf",
        "hf_id": "facebook/nllb-200-distilled-600M",
        "label": "NLLB-200 distilled 600M",
        "description": "Meilleure qualité, ~200 langues avec un seul modèle.",
        "size": "~2,5 Go",
        "offline": True,
        "kind": "single",
    },
    "m2m100_418M": {
        "backend": "hf",
        "hf_id": "facebook/m2m100_418M",
        "label": "M2M100 418M",
        "description": "Bonne qualité, ~100 langues, traduction directe entre paires.",
        "size": "~1,9 Go",
        "offline": True,
        "kind": "single",
    },
    "libretranslate": {
        "backend": "api",
        "label": "LibreTranslate (API)",
        "description": "Option EN LIGNE : instance LibreTranslate distante ou auto-hébergée.",
        "size": "—",
        "offline": False,
        "kind": "api",
    },
}


def _hf_model_dir(hf_id: str):
    return HF_HOME / "local" / hf_id.replace("/", "--")


def hf_installed(hf_id: str) -> bool:
    d = _hf_model_dir(hf_id)
    if not d.is_dir():
        return False
    return (
        any(d.glob("*.safetensors"))
        or any(d.glob("pytorch_model*.bin"))
        or any(d.glob("model.safetensors"))
    )


def hf_uninstall(hf_id: str) -> None:
    d = _hf_model_dir(hf_id)
    if d.is_dir():
        shutil.rmtree(d)


def argos_installed_pairs() -> list[dict]:
    """Paires installées, lues depuis les metadata.json des paquets Argos."""
    pairs = []
    if not ARGOS_PACKAGES.is_dir():
        return pairs
    for pkg in sorted(ARGOS_PACKAGES.iterdir()):
        meta = pkg / "metadata.json"
        if not meta.is_file():
            continue
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            pairs.append({
                "from": data["from_code"],
                "to": data["to_code"],
                "dir": pkg.name,
            })
        except Exception:
            continue
    return pairs


def argos_uninstall_pair(from_code: str, to_code: str) -> bool:
    removed = False
    for pair in argos_installed_pairs():
        if pair["from"] == from_code and pair["to"] == to_code:
            shutil.rmtree(ARGOS_PACKAGES / pair["dir"], ignore_errors=True)
            removed = True
    return removed


def model_status(model_id: str) -> dict:
    """État d'un modèle du catalogue, pour l'API."""
    info = CATALOG[model_id]
    entry = {"id": model_id, **{k: v for k, v in info.items() if k != "hf_id"}}
    if info["backend"] == "hf":
        entry["installed"] = hf_installed(info["hf_id"])
    elif info["backend"] == "argos":
        pairs = argos_installed_pairs()
        entry["installed"] = bool(pairs)
        entry["pairs"] = [{"from": p["from"], "to": p["to"]} for p in pairs]
    else:  # api
        entry["installed"] = True
    return entry


def usable_models(source: str, target: str) -> list[str]:
    """Modèles utilisables pour une paire donnée (installés et pertinents)."""
    usable = []
    for model_id, info in CATALOG.items():
        if info["backend"] == "hf" and hf_installed(info["hf_id"]):
            usable.append(model_id)
        elif info["backend"] == "argos":
            pairs = {(p["from"], p["to"]) for p in argos_installed_pairs()}
            direct = (source, target) in pairs
            pivot = (source, "en") in pairs and ("en", target) in pairs
            if direct or pivot:
                usable.append(model_id)
        elif info["backend"] == "api":
            usable.append(model_id)
    return usable
