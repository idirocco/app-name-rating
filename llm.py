"""OpenAI adapter. The key is read only from environment or Streamlit secrets."""

from __future__ import annotations

import json
import os
from typing import Any

from openai import OpenAI

from evaluator import LLM_DESIRABLE, MANDATORY


def get_api_key(secrets: Any) -> str | None:
    try:
        return secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
    except Exception:
        return os.getenv("OPENAI_API_KEY")


def _criterion_schema(mandatory: bool) -> dict[str, Any]:
    properties: dict[str, Any] = {
        "score": {"type": "integer", "minimum": 1, "maximum": 10},
        "reasoning": {"type": "string"},
    }
    required = ["score", "reasoning"]
    if mandatory:
        properties = {
            "status": {"type": "string", "enum": ["PASS", "FAIL", "REVIEW"]},
            **properties,
            "confidence": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH"]},
        }
        required = ["status", "score", "reasoning", "confidence"]
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


OUTPUT_SCHEMA = {
    "name": "brand_name_evaluation",
    "strict": True,
    "schema": {
        "type": "object",
        "properties": {
            "mandatory": {"type": "object", "properties": {key: _criterion_schema(True) for key in MANDATORY}, "required": list(MANDATORY), "additionalProperties": False},
            "desirable": {"type": "object", "properties": {key: _criterion_schema(False) for key in LLM_DESIRABLE}, "required": list(LLM_DESIRABLE), "additionalProperties": False},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "risks": {"type": "array", "items": {"type": "string"}},
            "recommendation": {"type": "string"},
        },
        "required": ["mandatory", "desirable", "strengths", "risks", "recommendation"],
        "additionalProperties": False,
    },
}


def _prompt(name: str, extra_context: str) -> str:
    return f"""Evalúa el nombre propuesto: {name!r}.

Contexto opcional del equipo: {extra_context or 'No se proporcionó contexto adicional.'}

Responde exclusivamente con el JSON solicitado. Todo el texto debe estar en español.
El producto es una plataforma tecnológica B2B2C global: los consumidores obtienen beneficios monetarios en comercios participantes y usan su saldo para reducir pagos de otros servicios. Puede evolucionar a lealtad, recompensas, pagos y servicios financieros.

Evalúa M1 idoneidad global (español, inglés y portugués), M2 pronunciación/escritura, M3 memorabilidad, M4 distintividad conceptual, M5 escalabilidad y M6 connotaciones negativas. Para cada M devuelve status PASS/FAIL/REVIEW, score entero 1-10, reasoning conciso y confidence LOW/MEDIUM/HIGH.

M4 es sólo conceptual: jamás afirmes ni insinúes que el nombre está disponible, registrado, no registrado o sin uso por competidores. M6: si no hay base suficiente para una interpretación negativa, usa REVIEW en vez de inventarla. D3 sonoridad, D4 identidad visual, D5 asociaciones positivas, D6 marca abstracta/evocativa, D7 consistencia digital y D8 versatilidad comercial devuelven score y reasoning. D7 es sólo lingüístico/usabilidad: no afirmes disponibilidad de dominios o usuarios.

No evalúes asuntos legales, marcas, dominios, redes ni conflictos comerciales. Distingue juicios subjetivos con expresiones como “parece” o “como impresión de marca”."""


def evaluate_with_llm(name: str, extra_context: str, model: str, api_key: str) -> dict[str, Any]:
    client = OpenAI(api_key=api_key)
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": "Eres un especialista riguroso en naming global. No haces afirmaciones legales ni de disponibilidad."}, {"role": "user", "content": _prompt(name, extra_context)}],
        response_format={"type": "json_schema", "json_schema": OUTPUT_SCHEMA},
        temperature=0.2,
    )
    content = completion.choices[0].message.content
    if not content:
        raise ValueError("El modelo no devolvió contenido evaluable.")
    return json.loads(content)
