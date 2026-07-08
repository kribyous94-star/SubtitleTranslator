"""Détection hors ligne de la langue source (langdetect)."""
from langdetect import DetectorFactory, detect

from .languages import LANGUAGES

DetectorFactory.seed = 0  # résultats déterministes

# langdetect renvoie parfois des codes régionaux
ALIASES = {"zh-cn": "zh", "zh-tw": "zh"}

SAMPLE_LINES = 80


def detect_language(texts: list[str]) -> str:
    """Détecte la langue sur un échantillon de répliques.

    Lève ValueError si la détection échoue ou donne une langue hors catalogue.
    """
    sample = " ".join(texts[:SAMPLE_LINES]).strip()
    if not sample:
        raise ValueError("Fichier sans texte exploitable pour la détection.")
    try:
        code = detect(sample)
    except Exception as exc:
        raise ValueError(f"Détection de langue impossible : {exc}") from exc
    code = ALIASES.get(code, code)
    if code not in LANGUAGES:
        raise ValueError(
            f"Langue détectée « {code} » non supportée — préciser la langue source."
        )
    return code
