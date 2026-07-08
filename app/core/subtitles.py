"""Lecture/écriture des fichiers de sous-titres via pysubs2.

Les horodatages et le style global sont préservés ; seul le texte des
répliques est remplacé. Les balises inline (<i>, {\\an8}…) sont retirées
avant traduction (v1 : on traduit le texte brut)."""
from pathlib import Path

import pysubs2

# extension -> format pysubs2
FORMATS = {
    ".srt": "srt",
    ".vtt": "vtt",
    ".ass": "ass",
    ".ssa": "ssa",
    ".sub": "microdvd",
    ".tmp": "tmp",
}

OUTPUT_FORMATS = {
    "srt": ".srt",
    "vtt": ".vtt",
    "ass": ".ass",
    "ssa": ".ssa",
    "microdvd": ".sub",
    "tmp": ".tmp",
}


class UnsupportedFormat(Exception):
    pass


def detect_format(path: Path) -> str:
    fmt = FORMATS.get(path.suffix.lower())
    if not fmt:
        raise UnsupportedFormat(
            f"Format non supporté : « {path.suffix} » (supportés : {', '.join(FORMATS)})"
        )
    return fmt


def load(path: Path) -> pysubs2.SSAFile:
    fmt = detect_format(path)
    try:
        return pysubs2.load(str(path), format_=fmt)
    except Exception as exc:  # fichiers MicroDVD sans fps, encodages exotiques…
        if fmt == "microdvd":
            return pysubs2.load(str(path), format_=fmt, fps=23.976)
        raise UnsupportedFormat(f"Impossible de lire le fichier : {exc}") from exc


def extract_texts(subs: pysubs2.SSAFile) -> tuple[list[int], list[str]]:
    """Retourne (indices des répliques à traduire, textes bruts).

    Les répliques vides ou de type commentaire sont laissées telles quelles.
    """
    indices, texts = [], []
    for i, line in enumerate(subs):
        if line.is_comment:
            continue
        text = line.plaintext.strip()
        if text:
            indices.append(i)
            texts.append(text)
    return indices, texts


def inject_texts(subs: pysubs2.SSAFile, indices: list[int], texts: list[str]) -> None:
    for i, text in zip(indices, texts):
        subs[i].plaintext = text.strip()


def save(subs: pysubs2.SSAFile, path: Path, fmt: str) -> None:
    if fmt not in OUTPUT_FORMATS:
        raise UnsupportedFormat(f"Format de sortie inconnu : {fmt}")
    subs.save(str(path), format_=fmt)


def output_filename(input_name: str, target_lang: str, fmt: str) -> str:
    stem = Path(input_name).stem
    return f"{stem}.{target_lang}{OUTPUT_FORMATS[fmt]}"
