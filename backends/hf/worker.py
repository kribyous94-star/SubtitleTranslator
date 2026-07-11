"""Worker Hugging Face (NLLB-200, M2M100) — s'exécute dans venvs/hf.

Le cache des modèles est confiné au dossier du projet via HF_HOME.
Pendant une traduction, l'application pose HF_HUB_OFFLINE=1 : aucun
accès réseau.

Commandes :
  translate --input in.json --output out.json --model facebook/nllb-200-distilled-600M --source fr --target en
  install   --model facebook/nllb-200-distilled-600M     (internet requis)
"""
import argparse
import json
import sys

BATCH_SIZE = 8

# ISO 639-1 -> code FLORES-200 (NLLB)
FLORES = {
    "fr": "fra_Latn", "en": "eng_Latn", "es": "spa_Latn", "de": "deu_Latn",
    "it": "ita_Latn", "pt": "por_Latn", "nl": "nld_Latn", "ru": "rus_Cyrl",
    "zh": "zho_Hans", "ja": "jpn_Jpan", "ko": "kor_Hang", "ar": "arb_Arab",
    "tr": "tur_Latn", "pl": "pol_Latn", "sv": "swe_Latn", "da": "dan_Latn",
    "fi": "fin_Latn", "no": "nob_Latn", "cs": "ces_Latn", "el": "ell_Grek",
    "he": "heb_Hebr", "hi": "hin_Deva", "id": "ind_Latn", "uk": "ukr_Cyrl",
    "ro": "ron_Latn", "hu": "hun_Latn", "bg": "bul_Cyrl", "th": "tha_Thai",
    "vi": "vie_Latn", "ca": "cat_Latn",
}


def emit(msg: dict) -> None:
    print(json.dumps(msg, ensure_ascii=False), flush=True)


def fail(message: str) -> None:
    emit({"type": "error", "message": message})
    sys.exit(1)


def _local_model_dir(model_id: str) -> str:
    """Chemin local sans symlinks pour un modèle (évite WinError 1314)."""
    import os
    hf_home = os.environ.get("HF_HOME", "")
    return os.path.join(hf_home, "local", model_id.replace("/", "--"))


def cmd_translate(args) -> None:
    import os
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    payload = json.loads(open(args.input, encoding="utf-8").read())
    texts = payload["texts"]
    is_nllb = "nllb" in args.model.lower()

    # Préférer le dossier local (copie directe, pas de symlinks) si disponible
    local_dir = _local_model_dir(args.model)
    model_path = local_dir if os.path.isdir(local_dir) else args.model

    if is_nllb:
        src, tgt = FLORES.get(args.source), FLORES.get(args.target)
        if not src or not tgt:
            fail(f"Langue non couverte par la table NLLB : {args.source} ou {args.target}.")
        tokenizer = AutoTokenizer.from_pretrained(model_path, src_lang=src)
        forced_bos = tokenizer.convert_tokens_to_ids(tgt)
    else:  # m2m100 : codes ISO 639-1 directement
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        tokenizer.src_lang = args.source
        try:
            forced_bos = tokenizer.get_lang_id(args.target)
        except KeyError:
            fail(f"Langue « {args.target} » non couverte par M2M100.")

    model = AutoModelForSeq2SeqLM.from_pretrained(model_path)
    model.eval()

    out: list[str] = []
    total = len(texts)
    with torch.inference_mode():
        for start in range(0, total, BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            enc = tokenizer(batch, return_tensors="pt", padding=True,
                            truncation=True, max_length=512)
            gen = model.generate(**enc, forced_bos_token_id=forced_bos,
                                 max_length=512, num_beams=2)
            out.extend(tokenizer.batch_decode(gen, skip_special_tokens=True))
            emit({"type": "progress", "value": min(1.0, (start + len(batch)) / total)})

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"texts": out}, f, ensure_ascii=False)
    emit({"type": "result", "count": total})


def cmd_install(args) -> None:
    import os
    import requests
    from fnmatch import fnmatch
    from huggingface_hub import HfApi, hf_hub_url

    PATTERNS = ["*.json", "*.model", "*.txt", "pytorch_model*.bin",
                "model.safetensors", "sentencepiece*", "tokenizer*"]
    CHUNK = 4 * 1024 * 1024  # 4 Mo par lecture

    local_dir = _local_model_dir(args.model)
    os.makedirs(local_dir, exist_ok=True)
    emit({"type": "progress", "value": 0.02})

    # Récupérer la liste des fichiers avec leur taille réelle
    api = HfApi()
    try:
        info = api.repo_info(args.model, repo_type="model", files_metadata=True)
    except Exception as exc:
        fail(f"Impossible d'accéder au dépôt {args.model} : {exc}")

    siblings = [
        s for s in (info.siblings or [])
        if any(fnmatch(s.rfilename, p) for p in PATTERNS)
    ]
    if not siblings:
        fail(f"Aucun fichier trouvé pour {args.model}.")

    total_bytes = sum(s.size or 0 for s in siblings)
    done_bytes = 0

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    for sibling in siblings:
        dest = os.path.join(local_dir, sibling.rfilename)
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Sauter si déjà présent et de la bonne taille
        file_size = sibling.size or 0
        if os.path.isfile(dest) and os.path.getsize(dest) == file_size:
            done_bytes += file_size
            emit({"type": "progress",
                  "value": 0.05 + 0.93 * done_bytes / max(total_bytes, 1)})
            continue

        url = hf_hub_url(args.model, sibling.rfilename)
        with requests.get(url, headers=headers, stream=True, timeout=120) as r:
            r.raise_for_status()
            file_done = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=CHUNK):
                    if not chunk:
                        continue
                    f.write(chunk)
                    file_done += len(chunk)
                    progress = 0.05 + 0.93 * (done_bytes + file_done) / max(total_bytes, 1)
                    emit({"type": "progress", "value": min(0.98, progress)})

        done_bytes += file_size

    emit({"type": "result", "installed": args.model})


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("translate")
    t.add_argument("--input", required=True)
    t.add_argument("--output", required=True)
    t.add_argument("--model", required=True)
    t.add_argument("--source", required=True)
    t.add_argument("--target", required=True)

    i = sub.add_parser("install")
    i.add_argument("--model", required=True)

    args = parser.parse_args()
    try:
        {"translate": cmd_translate, "install": cmd_install}[args.command](args)
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
