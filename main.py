from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import re
from pydantic import BaseModel
from fastapi.responses import HTMLResponse, JSONResponse
import uuid
import asyncio
from fastapi import BackgroundTasks
from typing import Dict, Optional


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = (BASE_DIR / "static").resolve()
PROJECTS_ROOT = (BASE_DIR / "proyectos").resolve()

PROGRAMAS_JSON = (STATIC_DIR / "data" / "programas.json").resolve()

app = FastAPI()

# ✅ Montaje único de recursos compartidos
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/proyectos", StaticFiles(directory=str(PROJECTS_ROOT)), name="proyectos")

PROJECT_ID_RE = re.compile(r"^[a-zA-Z0-9_-]{2,64}$")


def project_dir(project_id: str) -> Path:
    if not PROJECT_ID_RE.match(project_id):
        raise HTTPException(status_code=400, detail="project_id inválido")

    d = (PROJECTS_ROOT / project_id).resolve()
    if PROJECTS_ROOT not in d.parents:
        raise HTTPException(status_code=400, detail="Ruta inválida")
    if not d.exists():
        raise HTTPException(status_code=404, detail=f"Proyecto no existe: {project_id}")
    return d


def safe_join(root: Path, rel_path: str) -> Path:
    p = (root / rel_path).resolve()
    if root not in p.parents and p != root:
        raise HTTPException(status_code=400, detail="Ruta inválida")
    return p

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return FileResponse("static/favicon.png")

# Algunos navegadores (o algo en tu HTML) lo está pidiendo con slash final:
@app.get("/favicon.ico/", include_in_schema=False)
def favicon_slash():
    return FileResponse("static/favicon.png")

# ✅ Endpoint COMPARTIDO (no depende del proyecto)
@app.get("/api/programas")
def api_programas():
    if not PROGRAMAS_JSON.exists():
        raise HTTPException(status_code=404, detail="static/data/programas.json no encontrado")
    data = json.loads(PROGRAMAS_JSON.read_text(encoding="utf-8"))
    return JSONResponse(data)


# ✅ Entrada por proyecto: /proy1/
@app.get("/{project_id}/", response_class=HTMLResponse)
def entry(project_id: str):
    _ = project_dir(project_id)
    shell_path = STATIC_DIR / "shell.html"
    if not shell_path.exists():
        raise HTTPException(status_code=404, detail="static/shell.html no encontrado")

    html = shell_path.read_text(encoding="utf-8")
    html = html.replace("{{BASE_URL}}", f"/{project_id}")
    html = html.replace("{{PROJECT_ID}}", project_id)
    return HTMLResponse(html)


# ✅ API por proyecto (la que ya tenías)
@app.get("/{project_id}/api/estado")
def api_estado(project_id: str):
    d = project_dir(project_id)
    p = d / "estado.json"
    print("Buscando estado.json en ", p)
    if p.exists():
        return JSONResponse(json.loads(p.read_text(encoding="utf-8")))
    print("No se encontró estado.json, ", d)
    return {"titulo": f"nombre {project_id}", "descripcion": "Inicial"}

@app.put("/{project_id}/api/estado")
def put_estado(project_id: str, payload: dict = Body(...)):
    d = project_dir(project_id)
    p = d / "estado.json"

    try:
        p.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo escribir estado.json: {e}")

    return JSONResponse({
        "ok": True,
        "path": str(p),
        "programas": len(payload.get("informacion_programas_nacionales", []))
    })


# ✅ API por proyecto (la que ya tenías)
@app.get("/{project_id}/api/seleccion")
def api_seleccion(project_id: str):
    d = project_dir(project_id)
    p = d / "seleccion.json"
    print("Buscando seleccion.json en ", p)
    if p.exists():
        return JSONResponse(json.loads(p.read_text(encoding="utf-8")))
    print("No se encontró seleccion.json, ", d)
    return {""}


# ✅ Archivos específicos del proyecto: /proy1/files/...
@app.get("/{project_id}/files/{path:path}")
def project_files(project_id: str, path: str):
    d = project_dir(project_id)
    f = safe_join(d, path)
    if not f.exists() or not f.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(str(f))

@app.put("/{project_id}/api/seleccion")
def put_seleccion(project_id: str, payload: dict = Body(...)):
    d = project_dir(project_id)
    p = d / "seleccion.json"

    # Guarda JSON bonito (y UTF-8)
    try:
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo escribir seleccion.json: {e}")

    return JSONResponse({"ok": True, "path": str(p), "count": payload.get("count")})

from lector import correr_snies
@app.get("/{project_id}/snies")
def run_snies(project_id: str):
    print(f"Recibida solicitud para correr SNIES en proyecto {project_id}")
    correr_snies(project_id)
    return {"status": "SNIES analysis completed", "project_id": project_id}

from agentes_de_analisis import correr_analisis, pagina_temporal
@app.get("/{project_id}/reporte")
def run_reporte(project_id: str):
    print(f"Recibida solicitud para Generar el reporte en proyecto {project_id}")
    pagina_temporal(project_id)
    correr_analisis(project_id)
    
    return RedirectResponse(
        url=f"/{project_id}/files/reporte.html",
        status_code=302
    )
from programa_autofill import autofill_programa
import markdown 
@app.post("/{project_id}/api/autofill")
def post_programa_autofill(project_id: str, payload: dict = Body(...)):
    try:
        programa = payload.get("programa")
        if not isinstance(programa, dict):
            raise ValueError("Body inválido: se esperaba { programaIndex, programa }")

        result = autofill_programa(project_id=project_id, programa=programa)

        # opcional: re-incluir el index para que el front lo use
        if "programaIndex" in payload:
            result["programaIndex"] = payload["programaIndex"]

        return JSONResponse(result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fallo autofill: {e}")