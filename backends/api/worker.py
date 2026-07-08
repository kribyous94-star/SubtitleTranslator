"""Worker LibreTranslate — option EN LIGNE, s'exécute dans le venv « app ».

Appelle une instance LibreTranslate (URL et clé API lues dans data/config.json,
configurables depuis l'interface). Le cœur du projet reste hors ligne : ce
backend n'est qu'une option.

Commande :
  translate --input in.json --output out.json --source fr --target en --config data/config.json
"""
import argparse
import json
import sys

import requests

BATCH_SIZE = 25
TIMEOUT = 60


def emit(msg: dict) -> None:
    print(json.dumps(msg, ensure_ascii=False), flush=True)


def fail(message: str) -> None:
    emit({"type": "error", "message": message})
    sys.exit(1)


def cmd_translate(args) -> None:
    try:
        config = json.loads(open(args.config, encoding="utf-8").read())
    except FileNotFoundError:
        config = {}
    url = (config.get("libretranslate_url") or "").rstrip("/")
    if not url:
        fail("URL LibreTranslate non configurée (onglet Modèles → LibreTranslate).")
    api_key = config.get("libretranslate_api_key") or ""

    payload = json.loads(open(args.input, encoding="utf-8").read())
    texts = payload["texts"]
    out: list[str] = []
    total = len(texts)
    for start in range(0, total, BATCH_SIZE):
        batch = texts[start:start + BATCH_SIZE]
        body = {"q": batch, "source": args.source, "target": args.target,
                "format": "text"}
        if api_key:
            body["api_key"] = api_key
        try:
            resp = requests.post(f"{url}/translate", json=body, timeout=TIMEOUT)
        except requests.RequestException as exc:
            fail(f"Instance LibreTranslate injoignable : {exc}")
        if resp.status_code != 200:
            detail = resp.json().get("error", resp.text[:200]) if resp.text else resp.status_code
            fail(f"Erreur LibreTranslate : {detail}")
        translated = resp.json()["translatedText"]
        out.extend(translated if isinstance(translated, list) else [translated])
        emit({"type": "progress", "value": min(1.0, (start + len(batch)) / total)})

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"texts": out}, f, ensure_ascii=False)
    emit({"type": "result", "count": total})


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    t = sub.add_parser("translate")
    t.add_argument("--input", required=True)
    t.add_argument("--output", required=True)
    t.add_argument("--source", required=True)
    t.add_argument("--target", required=True)
    t.add_argument("--config", required=True)
    args = parser.parse_args()
    try:
        cmd_translate(args)
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
