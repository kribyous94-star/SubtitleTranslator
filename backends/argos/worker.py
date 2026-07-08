"""Worker Argos Translate — s'exécute dans venvs/argos.

Les paquets de langues sont confinés au dossier du projet via
ARGOS_PACKAGES_DIR (posé par l'application avant le lancement).

Commandes :
  translate --input in.json --output out.json --source en --target fr
  install   --pair en:fr        (internet requis)
  uninstall --pair en:fr
  available                     (paires installables, internet requis)
"""
import argparse
import json
import sys


def emit(msg: dict) -> None:
    print(json.dumps(msg, ensure_ascii=False), flush=True)


def fail(message: str) -> None:
    emit({"type": "error", "message": message})
    sys.exit(1)


def get_translation(source: str, target: str):
    import argostranslate.translate as tr
    langs = {l.code: l for l in tr.get_installed_languages()}
    if source not in langs or target not in langs:
        fail(f"Paire {source} → {target} non installée (onglet Modèles).")
    translation = langs[source].get_translation(langs[target])
    if translation is None:
        fail(
            f"Aucun chemin de traduction {source} → {target} : installer la paire "
            f"directe, ou les paires {source} → en et en → {target} (pivot)."
        )
    return translation


def cmd_translate(args) -> None:
    payload = json.loads(open(args.input, encoding="utf-8").read())
    texts = payload["texts"]
    translation = get_translation(args.source, args.target)
    out = []
    total = len(texts)
    for i, text in enumerate(texts):
        out.append(translation.translate(text))
        if i % 10 == 0 or i == total - 1:
            emit({"type": "progress", "value": (i + 1) / total})
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump({"texts": out}, f, ensure_ascii=False)
    emit({"type": "result", "count": total})


def parse_pair(pair: str) -> tuple[str, str]:
    if ":" not in pair:
        fail("Paire attendue au format « en:fr ».")
    src, dst = pair.split(":", 1)
    return src.strip(), dst.strip()


def cmd_install(args) -> None:
    import argostranslate.package as pkg
    src, dst = parse_pair(args.pair)
    emit({"type": "progress", "value": 0.05})
    pkg.update_package_index()
    emit({"type": "progress", "value": 0.15})
    available = pkg.get_available_packages()
    match = next((p for p in available if p.from_code == src and p.to_code == dst), None)
    if match is None:
        fail(
            f"La paire {src} → {dst} n'existe pas dans l'index Argos. "
            f"Astuce : installer {src} → en puis en → {dst} (pivot par l'anglais)."
        )
    emit({"type": "progress", "value": 0.2})
    download_path = match.download()
    emit({"type": "progress", "value": 0.9})
    pkg.install_from_path(download_path)
    emit({"type": "result", "installed": f"{src}:{dst}"})


def cmd_uninstall(args) -> None:
    import argostranslate.package as pkg
    src, dst = parse_pair(args.pair)
    for installed in pkg.get_installed_packages():
        if installed.from_code == src and installed.to_code == dst:
            pkg.uninstall(installed)
            emit({"type": "result", "uninstalled": f"{src}:{dst}"})
            return
    fail(f"Paire {src} → {dst} non installée.")


def cmd_available(_args) -> None:
    import argostranslate.package as pkg
    pkg.update_package_index()
    pairs = [
        {"from": p.from_code, "to": p.to_code,
         "from_name": p.from_name, "to_name": p.to_name}
        for p in pkg.get_available_packages()
    ]
    emit({"type": "result", "pairs": pairs})


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    t = sub.add_parser("translate")
    t.add_argument("--input", required=True)
    t.add_argument("--output", required=True)
    t.add_argument("--source", required=True)
    t.add_argument("--target", required=True)

    i = sub.add_parser("install")
    i.add_argument("--pair", required=True)

    u = sub.add_parser("uninstall")
    u.add_argument("--pair", required=True)

    sub.add_parser("available")

    args = parser.parse_args()
    try:
        {"translate": cmd_translate, "install": cmd_install,
         "uninstall": cmd_uninstall, "available": cmd_available}[args.command](args)
    except SystemExit:
        raise
    except Exception as exc:
        fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
