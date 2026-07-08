"""Serveur SubtitleTranslator : API + interface web locale."""
import json

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core import installs, jobs, registry
from app.core.languages import LANGUAGES
from app.core.paths import CONFIG_FILE, STATIC, ensure_dirs
from app.core.subtitles import FORMATS, OUTPUT_FORMATS
from app.core.workers import WorkerError

ensure_dirs()
app = FastAPI(title="SubtitleTranslator")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/languages")
def api_languages():
    return {
        "languages": [{"code": c, "name": n} for c, n in sorted(LANGUAGES.items(), key=lambda x: x[1])],
        "input_formats": sorted(FORMATS.keys()),
        "output_formats": list(OUTPUT_FORMATS.keys()),
    }


@app.get("/api/models")
def api_models():
    tasks = installs.get_tasks()
    models = []
    for model_id in registry.CATALOG:
        entry = registry.model_status(model_id)
        entry["tasks"] = {k: v for k, v in tasks.items() if k.split(":")[0] == model_id}
        models.append(entry)
    return {"models": models}


@app.post("/api/models/install")
def api_install(body: dict):
    model_id = body.get("model_id", "")
    if model_id not in registry.CATALOG:
        raise HTTPException(404, "Modèle inconnu.")
    installs.clear_error(model_id, body.get("pair"))
    key = installs.start_install(model_id, body.get("pair"))
    return {"task": key}


@app.post("/api/models/uninstall")
def api_uninstall(body: dict):
    model_id = body.get("model_id", "")
    if model_id not in registry.CATALOG:
        raise HTTPException(404, "Modèle inconnu.")
    try:
        installs.uninstall(model_id, body.get("pair"))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.get("/api/models/argos/available")
def api_argos_available():
    try:
        return {"pairs": installs.argos_available_pairs()}
    except WorkerError as exc:
        raise HTTPException(502, f"Index Argos inaccessible (internet requis) : {exc}")


@app.get("/api/config")
def api_get_config():
    if CONFIG_FILE.is_file():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {"libretranslate_url": "", "libretranslate_api_key": ""}


@app.post("/api/config")
def api_set_config(body: dict):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(body, indent=2), encoding="utf-8")
    return {"ok": True}


@app.post("/api/jobs")
async def api_create_job(
    file: UploadFile = File(...),
    source: str = Form("auto"),
    target: str = Form(...),
    model: str = Form(...),
    out_format: str = Form(""),
):
    if target not in LANGUAGES:
        raise HTTPException(400, "Langue cible inconnue.")
    if source != "auto" and source not in LANGUAGES:
        raise HTTPException(400, "Langue source inconnue.")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Fichier vide.")
    try:
        job = jobs.create_job(file.filename or "subtitles.srt", content,
                              source, target, model, out_format or None)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return job.to_dict()


@app.get("/api/jobs/{job_id}")
def api_job(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job inconnu.")
    return job.to_dict()


@app.get("/api/jobs/{job_id}/download")
def api_download(job_id: str):
    job = jobs.get_job(job_id)
    if not job or job.status != "done" or not job.output_name:
        raise HTTPException(404, "Résultat indisponible.")
    return FileResponse(job.dir / job.output_name, filename=job.output_name,
                        media_type="application/octet-stream")


@app.exception_handler(WorkerError)
def worker_error_handler(_, exc: WorkerError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


app.mount("/static", StaticFiles(directory=str(STATIC)), name="static")
