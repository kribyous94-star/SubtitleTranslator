"""Lancement des workers de traduction dans leurs venvs respectifs.

L'application n'importe jamais les bibliothèques de traduction : chaque
backend est un sous-processus lancé avec le python de son venv, confiné
au dossier du projet par variables d'environnement."""
import json
import os
import subprocess
import sys
import threading
import time
from typing import Callable

# Secondes sans aucun message du worker avant abandon (traduction d'un gros fichier)
WORKER_TIMEOUT = 600  # 10 minutes

from .paths import ARGOS_PACKAGES, BACKENDS, CACHE, HF_HOME, ROOT, VENVS, XDG_DATA

# le backend « api » est léger : il tourne dans le venv « app »
WORKER_VENV = {"argos": "argos", "hf": "hf", "api": "app"}

# Sur Windows : venvs/<nom>/Scripts/python.exe
# Sur Unix    : venvs/<nom>/bin/python
def _venv_python(venv_name: str):
    if sys.platform == "win32":
        return VENVS / venv_name / "Scripts" / "python.exe"
    return VENVS / venv_name / "bin" / "python"


class WorkerError(Exception):
    pass


def worker_env(offline: bool) -> dict:
    env = os.environ.copy()
    env["HF_HOME"] = str(HF_HOME)
    env["ARGOS_PACKAGES_DIR"] = str(ARGOS_PACKAGES)
    env["XDG_DATA_HOME"] = str(XDG_DATA)
    env["XDG_CACHE_HOME"] = str(CACHE)
    if offline:
        # aucun accès réseau pendant une traduction, même par accident
        env["HF_HUB_OFFLINE"] = "1"
        env["TRANSFORMERS_OFFLINE"] = "1"
    return env


def run_worker(
    backend: str,
    args: list[str],
    on_progress: Callable[[float], None] | None = None,
    offline: bool = False,
) -> dict:
    """Exécute un worker et retourne son message {"type": "result", ...}.

    Le worker écrit sur stdout des lignes JSON : progress, log, result, error.
    """
    python = _venv_python(WORKER_VENV[backend])
    if not python.exists():
        script = "install.ps1" if sys.platform == "win32" else "install.sh"
        raise WorkerError(
            f"Le venv du backend « {backend} » n'est pas installé (relancer ./{script})."
        )
    cmd = [str(python), str(BACKENDS / backend / "worker.py"), *args]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=worker_env(offline),
        cwd=str(ROOT),
    )
    result = None
    error = None
    last_msg_time = time.monotonic()

    def _watchdog() -> None:
        while proc.poll() is None:
            if time.monotonic() - last_msg_time > WORKER_TIMEOUT:
                proc.kill()
                break
            time.sleep(10)

    wd = threading.Thread(target=_watchdog, daemon=True)
    wd.start()

    assert proc.stdout is not None
    for raw in proc.stdout:
        raw = raw.strip()
        if not raw:
            continue
        last_msg_time = time.monotonic()
        try:
            msg = json.loads(raw)
        except ValueError:
            continue  # bruit d'une bibliothèque sur stdout
        if msg.get("type") == "progress" and on_progress:
            on_progress(float(msg.get("value", 0.0)))
        elif msg.get("type") == "result":
            result = msg
        elif msg.get("type") == "error":
            error = msg.get("message", "erreur inconnue")
    stderr = proc.stderr.read() if proc.stderr else ""
    proc.wait()
    if error:
        raise WorkerError(error)
    if proc.returncode != 0:
        tail = "\n".join(stderr.strip().splitlines()[-5:])
        raise WorkerError(f"Le worker « {backend} » a échoué (code {proc.returncode}) : {tail}")
    if result is None:
        raise WorkerError(f"Le worker « {backend} » n'a renvoyé aucun résultat.")
    return result
