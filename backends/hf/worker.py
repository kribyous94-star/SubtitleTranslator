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

BATCH_SIZE = 16

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


def cmd_translate(args) -> None:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    payload = json.loads(open(args.input, encoding="utf-8").read())
    texts = payload["texts"]
    is_nllb = "nllb" in args.model.lower()

    if is_nllb:
        src, tgt = FLORES.get(args.source), FLORES.get(args.target)
        if not src or not tgt:
            fail(f"Langue non couverte par la table NLLB : {args.source} ou {args.target}.")
        tokenizer = AutoTokenizer.from_pretrained(args.model, src_lang=src)
        forced_bos = tokenizer.convert_tokens_to_ids(tgt)
    else:  # m2m100 : codes ISO 639-1 directement
        tokenizer = AutoTokenizer.from_pretrained(args.model)
        tokenizer.src_lang = args.source
        try:
            forced_bos = tokenizer.get_lang_id(args.target)
        except KeyError:
            fail(f"Langue « {args.target} » non couverte par M2M100.")

    model = AutoModelForSeq2SeqLM.from_pretrained(args.model)
    model.eval()

    out: list[str] = []
    total = len(texts)
    with torch.inference_mode():
        for start in range(0, total, BATCH_SIZE):
            batch = texts[start:start + BATCH_SIZE]
            enc = tokenizer(batch, return_tensors="pt", padding=True,
                            truncation=True, max_length=512)
            gen = model.generate(**enc, forced_bos_token_id=forced_bos,
                                 max_length=512, num_beams=4)
            out.extend(tokenizer.batch_decode(gen, skip_special_tokens=True))
            emit({"type": "progress", "value": min(1.0, (start + len(batch)) / total)})

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"texts": out}, f, ensure_ascii=False)
    emit({"type": "result", "count": total})


def cmd_install(args) -> None:
    from huggingface_hub import snapshot_download

    emit({"type": "progress", "value": 0.02})
    # tqdm affiche sur stderr ; on se contente d'un progrès grossier ici,
    # le téléchargement étant repris automatiquement s'il est interrompu.
    snapshot_download(
        repo_id=args.model,
        allow_patterns=["*.json", "*.model", "*.txt",
                        "pytorch_model.bin", "model.safetensors",
                        "sentencepiece*", "tokenizer*"],
    )
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
