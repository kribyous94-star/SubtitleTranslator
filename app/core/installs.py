"""Installation/désinstallation des modèles depuis l'interface.

Les téléchargements (internet requis) tournent en tâche de fond ; l'état
est exposé via /api/models. Les désinstallations sont synchrones (simple
suppression de dossiers dans models/)."""
import threading

from . import registry
from .workers import run_worker

_LOCK = threading.Lock()
# clé de tâche -> {"status": "installing"|"error", "progress": float, "error": str|None}
_TASKS: dict[str, dict] = {}


def task_key(model_id: str, pair: str | None = None) -> str:
    return f"{model_id}:{pair}" if pair else model_id


def get_tasks() -> dict:
    with _LOCK:
        return {k: dict(v) for k, v in _TASKS.items()}


def start_install(model_id: str, pair: str | None = None) -> str:
    """Lance l'installation en tâche de fond. Retourne la clé de tâche."""
    info = registry.CATALOG[model_id]
    key = task_key(model_id, pair)
    with _LOCK:
        if key in _TASKS and _TASKS[key]["status"] == "installing":
            return key  # déjà en cours
        _TASKS[key] = {"status": "installing", "progress": 0.0, "error": None}

    def work() -> None:
        try:
            if info["backend"] == "argos":
                if not pair or ":" not in pair:
                    raise ValueError("Paire attendue au format « en:fr ».")
                args = ["install", "--pair", pair]
            elif info["backend"] == "hf":
                args = ["install", "--model", info["hf_id"]]
            else:
                raise ValueError("Ce backend n'a rien à installer.")

            def on_progress(value: float) -> None:
                with _LOCK:
                    _TASKS[key]["progress"] = value

            run_worker(info["backend"], args, on_progress=on_progress, offline=False)
            with _LOCK:
                del _TASKS[key]  # terminé : l'état « installé » vient de registry
        except Exception as exc:
            with _LOCK:
                _TASKS[key] = {"status": "error", "progress": 0.0, "error": str(exc)}

    threading.Thread(target=work, daemon=True).start()
    return key


def clear_error(model_id: str, pair: str | None = None) -> None:
    with _LOCK:
        _TASKS.pop(task_key(model_id, pair), None)


def uninstall(model_id: str, pair: str | None = None) -> None:
    info = registry.CATALOG[model_id]
    if info["backend"] == "hf":
        registry.hf_uninstall(info["hf_id"])
    elif info["backend"] == "argos":
        if not pair or ":" not in pair:
            raise ValueError("Paire attendue au format « en:fr ».")
        src, dst = pair.split(":", 1)
        if not registry.argos_uninstall_pair(src, dst):
            raise ValueError(f"Paire {src} → {dst} non installée.")
    else:
        raise ValueError("Ce backend n'a rien à désinstaller.")


def argos_available_pairs() -> list[dict]:
    """Paires installables (interroge l'index Argos — internet requis)."""
    result = run_worker("argos", ["available"], offline=False)
    return result.get("pairs", [])
