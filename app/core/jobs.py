"""Jobs de traduction : un thread par job, suivi par polling."""
import json
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path

from . import subtitles
from .detect import detect_language
from .paths import CONFIG_FILE, JOBS_DIR
from .registry import CATALOG
from .workers import run_worker

_LOCK = threading.Lock()
_JOBS: dict[str, "Job"] = {}


@dataclass
class Job:
    id: str
    filename: str
    source: str            # code langue ou "auto"
    target: str
    model: str
    out_format: str
    status: str = "pending"   # pending | running | done | error
    progress: float = 0.0
    detected: str | None = None
    output_name: str | None = None
    error: str | None = None

    @property
    def dir(self) -> Path:
        return JOBS_DIR / self.id

    def to_dict(self) -> dict:
        return {
            "id": self.id, "filename": self.filename, "source": self.source,
            "target": self.target, "model": self.model, "status": self.status,
            "progress": round(self.progress, 3), "detected": self.detected,
            "output_name": self.output_name, "error": self.error,
        }


def get_job(job_id: str) -> Job | None:
    with _LOCK:
        return _JOBS.get(job_id)


def create_job(filename: str, content: bytes, source: str, target: str,
               model: str, out_format: str | None) -> Job:
    if model not in CATALOG:
        raise ValueError(f"Modèle inconnu : {model}")
    job = Job(
        id=uuid.uuid4().hex[:12],
        filename=filename,
        source=source,
        target=target,
        model=model,
        out_format=out_format or "",
    )
    job.dir.mkdir(parents=True, exist_ok=True)
    (job.dir / filename).write_bytes(content)
    with _LOCK:
        _JOBS[job.id] = job
    threading.Thread(target=_run, args=(job,), daemon=True).start()
    return job


def _run(job: Job) -> None:
    try:
        job.status = "running"
        input_path = job.dir / job.filename
        in_format = subtitles.detect_format(input_path)
        out_format = job.out_format or in_format
        subs = subtitles.load(input_path)
        indices, texts = subtitles.extract_texts(subs)
        if not texts:
            raise ValueError("Aucun texte à traduire dans ce fichier.")

        source = job.source
        if source == "auto":
            source = detect_language(texts)
            job.detected = source
        if source == job.target:
            raise ValueError("Langues source et cible identiques.")

        model_info = CATALOG[job.model]
        payload = {"texts": texts}
        in_json = job.dir / "worker_in.json"
        out_json = job.dir / "worker_out.json"
        in_json.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        args = [
            "translate",
            "--input", str(in_json), "--output", str(out_json),
            "--source", source, "--target", job.target,
        ]
        if model_info["backend"] == "hf":
            args += ["--model", model_info["hf_id"]]
        elif model_info["backend"] == "api":
            args += ["--config", str(CONFIG_FILE)]

        def on_progress(value: float) -> None:
            job.progress = value

        # traduction strictement hors ligne, sauf backend api
        run_worker(model_info["backend"], args,
                   on_progress=on_progress, offline=model_info["offline"])

        translated = json.loads(out_json.read_text(encoding="utf-8"))["texts"]
        if len(translated) != len(texts):
            raise ValueError("Le worker a renvoyé un nombre de lignes inattendu.")
        subtitles.inject_texts(subs, indices, translated)

        job.output_name = subtitles.output_filename(job.filename, job.target, out_format)
        subtitles.save(subs, job.dir / job.output_name, out_format)
        job.progress = 1.0
        job.status = "done"
    except Exception as exc:
        job.status = "error"
        job.error = str(exc)
