import os
import json
from typing import Dict, Any, List

from openai import OpenAI
from openai import APIStatusError, AuthenticationError, RateLimitError, APITimeoutError
import logging, json, os

client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def _normalize_plan(lines: List[str]) -> List[str]:
    out = []
    seen = set()
    for s in lines or []:
        s2 = " ".join(str(s).strip().split())
        if not s2:
            continue
        k = s2.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(s2)
    return out


def autofill_programa(project_id: str, programa: Dict[str, Any]) -> Dict[str, Any]:
    # Validación mínima (ajústala a tus reglas)
    #print('Programa recibido para autofill:', programa)
    for k in ["Programa", "Institucion", "Municipio", "URL"]:
        if not str(programa.get(k, "")).strip():
            raise ValueError(f"Falta campo requerido: {k}")
    #print('Lectura de información del programa exitosa, preparando prompt...')
    
    snies = str(programa.get("Snies", "")).strip()
    nombre = str(programa.get("Programa", "")).strip()
    inst = str(programa.get("Institucion", "")).strip()
    muni = str(programa.get("Municipio", "")).strip()
    url_inst = str(programa.get("URL", "")).strip()
    url_prog = str(programa.get("URL_programa", "")).strip()
    #print('Información del programa procesada, llamando a LLM para autofill...')
    schema = {
        "type": "object",
        "properties": {
            "applied": {"type": "boolean"},
            "reason": {"type": "string"},
            "patch": {
            "type": "object",
            "properties": {
                "URL_programa": {"type": "string"},
                "Descripcion": {"type": "string"},
                "Perfil": {"type": "string"},
                "Plan_de_estudios": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["URL_programa", "Descripcion", "Perfil", "Plan_de_estudios"],
            "additionalProperties": False
            },
            "sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                "url": {"type": "string"}
                },
                "required": ["url"],
                "additionalProperties": False
            }
            }
        },
        "required": ["applied", "reason", "patch", "sources"],
        "additionalProperties": False
    }

    prompt = f"""
Completa información de un programa académico con evidencia desde la web (prioriza sitio oficial de la institución).
Datos base:
- SNIES: {snies}
- Programa: {nombre}
- Institución: {inst}
- Municipio: {muni}
- URL institución: {url_inst}
- URL programa (si existe): {url_prog}

Devuelve:
- Descripcion (texto)
- Perfil (texto)
- Plan_de_estudios (lista de cursos; si está por semestres, aplana)
- URL_programa si la encuentras.

Reglas:
- No inventes.
- Si NO encuentras evidencia clara para (plan) y (perfil o descripción), responde applied=false.
- Incluye sources (urls).
"""
    #print('Prompt preparado, llamando a LLM...')
    logger = logging.getLogger("autofill")
    # Llamada con búsqueda web (tool web_search)
    try:
        resp= client.responses.create(
            model="gpt-4.1",  # prueba esto primero
            input=prompt,
            tools=[{"type": "web_search"}],
            text={"format": {"type": "json_schema", "name": "programa_autofill", "schema": schema}},
        )
        #print('Respuesta recibida del LLM, procesando...'+str(resp.output_text))
        data = json.loads(resp.output_text)

        if not data.get("applied"):
            return {
                "applied": False,
                "reason": data.get("reason", "Sin evidencia suficiente"),
            }

        patch = data.get("patch") or {}
        patch["Plan_de_estudios"] = _normalize_plan(patch.get("Plan_de_estudios", []))

        # Reglas de mínimo para aplicar (ajusta si quieres)
        if (not patch.get("Descripcion") and not patch.get("Perfil")) or len(patch["Plan_de_estudios"]) == 0:
            return {"applied": False, "reason": "No se halló información suficiente (plan/perfil/descripcion)"}

        # Esto es lo que tu página aplica directo con Object.assign(...)
        return {
            "applied": True,
            "patch": patch,
            "sources": data.get("sources", []),
        }
    except AuthenticationError as e:
        logger.exception("Auth error OpenAI (API key/permissions).")
        raise
    except RateLimitError as e:
        logger.exception("Rate limit OpenAI.")
        raise
    except APITimeoutError as e:
        logger.exception("Timeout OpenAI.")
        raise
    except APIStatusError as e:
        # Esto te da el error “real” del API: 400/401/403/404/500
        rid = getattr(e, "request_id", None)
        logger.error("OpenAI APIStatusError status=%s request_id=%s", e.status_code, rid)
        # Muchas veces e.response tiene JSON con 'error'
        try:
            logger.error("OpenAI error body: %s", e.response.json())
        except Exception:
            logger.error("OpenAI error raw: %s", str(e))
        
    
