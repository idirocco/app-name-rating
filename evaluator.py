"""Pure evaluation helpers for the Brand Name Evaluator.

All score aggregation and eligibility decisions live here so an LLM can never
override a mandatory failure or calculate the final ranking incorrectly.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

MANDATORY = {
    "M1": "Idoneidad global",
    "M2": "Pronunciación y escritura",
    "M3": "Memorabilidad",
    "M4": "Distintividad conceptual",
    "M5": "Escalabilidad",
    "M6": "Connotaciones negativas",
}
LLM_DESIRABLE = {
    "D3": "Sonoridad",
    "D4": "Potencial de identidad visual",
    "D5": "Asociaciones positivas",
    "D6": "Marca abstracta o evocativa",
    "D7": "Consistencia de nombre digital",
    "D8": "Versatilidad comercial",
}
VALID_STATUSES = {"PASS", "FAIL", "REVIEW"}
VALID_CONFIDENCE = {"LOW", "MEDIUM", "HIGH"}


def normalize_name(name: str) -> str:
    """Return a display-safe candidate name without internal line breaks."""
    return " ".join(name.strip().split())


def unicode_letter_count(name: str) -> int:
    return sum(char.isalpha() for char in name)


def estimate_spanish_syllables(name: str) -> tuple[int, bool]:
    """Heuristic Spanish syllable estimate.

    It counts vowel groups, treating common Spanish weak-vowel combinations as
    diphthongs. Invented words, acronyms, non-letter characters, and uncommon
    consonant patterns are explicitly marked as uncertain.
    """
    compact = "".join(char for char in name.lower() if char.isalpha())
    compact = unicodedata.normalize("NFD", compact)
    compact = "".join(char for char in compact if unicodedata.category(char) != "Mn")
    if not compact:
        return 0, True

    vowels = "aeiouü"
    groups = re.findall(f"[{vowels}]+", compact)
    count = 0
    for group in groups:
        if len(group) == 1:
            count += 1
        elif len(group) == 2 and group not in {"aa", "ee", "ii", "oo", "uu"}:
            # A pair with i/u normally forms one Spanish syllable; pairs of
            # strong vowels (ae, ao, ea, eo, oa, oe) normally form a hiatus.
            count += 1 if any(v in group for v in "iu") else 2
        else:
            # Triphthongs and hiatuses cannot be known reliably for coined names.
            count += 1 if ("i" in group or "u" in group) else len(group)

    uncertain = (
        bool(re.search(r"[^A-Za-zÁÉÍÓÚÜÑáéíóúüñ -]", name))
        or len(compact) < 3
        or bool(re.search(r"[kwxy]|[bcdfghjklmnñpqrstvwxyz]{3,}", compact))
        or any(part in compact for part in ("ai", "ei", "oi", "au", "eu", "ou"))
    )
    return max(count, 1), uncertain


def syllable_score(count: int) -> int:
    if count == 2:
        return 10
    if count == 3:
        return 7
    if count == 1:
        return 6
    if count == 4:
        return 3
    return 1


def length_score(letter_count: int) -> int:
    if 4 <= letter_count <= 6:
        return 10
    if 7 <= letter_count <= 8:
        return 7
    if letter_count == 3:
        return 6
    if letter_count > 8:
        return 3
    return 2


def deterministic_criteria(name: str) -> dict[str, dict[str, Any]]:
    syllables, uncertain = estimate_spanish_syllables(name)
    letters = unicode_letter_count(name)
    suffix = " Estimación heurística; la pronunciación de un nombre inventado puede variar." if uncertain else ""
    return {
        "D1": {
            "criterion": "Conteo de sílabas",
            "score": syllable_score(syllables),
            "reasoning": f"Estimación de {syllables} sílaba(s) para pronunciación española.{suffix}",
            "estimated_syllables": syllables,
            "uncertain": uncertain,
            "source": "Determinístico (heurístico)",
        },
        "D2": {
            "criterion": "Longitud del nombre",
            "score": length_score(letters),
            "reasoning": f"{letters} letra(s) Unicode; se excluyen espacios, números y símbolos.",
            "letter_count": letters,
            "source": "Determinístico",
        },
    }


def eligibility(mandatory: dict[str, dict[str, Any]]) -> str:
    statuses = [item["status"] for item in mandatory.values()]
    if "FAIL" in statuses:
        return "FAIL"
    if "REVIEW" in statuses:
        return "REVIEW"
    return "PASS"


def overall_score(mandatory: dict[str, dict[str, Any]], desirable: dict[str, dict[str, Any]]) -> float:
    dimensions = (
        ((mandatory["M2"]["score"] + desirable["D3"]["score"]) / 2, 20),
        (mandatory["M3"]["score"], 20),
        ((mandatory["M4"]["score"] + desirable["D6"]["score"]) / 2, 20),
        (mandatory["M1"]["score"], 15),
        (mandatory["M5"]["score"], 15),
        (desirable["D4"]["score"], 10),
    )
    return round(sum(score * weight for score, weight in dimensions) / 100, 1)


def _clean_llm_criterion(item: Any, code: str, mandatory: bool) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError(f"El modelo no devolvió un objeto válido para {code}.")
    score = item.get("score")
    if not isinstance(score, int) or isinstance(score, bool) or not 1 <= score <= 10:
        raise ValueError(f"La puntuación de {code} debe ser un entero entre 1 y 10.")
    reasoning = item.get("reasoning")
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise ValueError(f"Falta una explicación para {code}.")
    clean = {"criterion": (MANDATORY if mandatory else LLM_DESIRABLE)[code], "score": score, "reasoning": reasoning.strip(), "source": "LLM"}
    if mandatory:
        status = item.get("status")
        confidence = item.get("confidence")
        if status not in VALID_STATUSES or confidence not in VALID_CONFIDENCE:
            raise ValueError(f"{code} contiene estado o confianza no válidos.")
        clean.update(status=status, confidence=confidence)
    return clean


def build_evaluation(name: str, llm_result: dict[str, Any]) -> dict[str, Any]:
    """Validate model output and combine it with local calculations."""
    if not isinstance(llm_result, dict):
        raise ValueError("La respuesta del modelo no es un objeto JSON.")
    raw_mandatory = llm_result.get("mandatory")
    raw_desirable = llm_result.get("desirable")
    if not isinstance(raw_mandatory, dict) or not isinstance(raw_desirable, dict):
        raise ValueError("La respuesta no contiene los grupos de criterios requeridos.")

    mandatory = {code: _clean_llm_criterion(raw_mandatory.get(code), code, True) for code in MANDATORY}
    desirable = deterministic_criteria(name)
    desirable.update({code: _clean_llm_criterion(raw_desirable.get(code), code, False) for code in LLM_DESIRABLE})
    strengths = llm_result.get("strengths", [])
    risks = llm_result.get("risks", [])
    recommendation = llm_result.get("recommendation", "")
    if not all(isinstance(value, list) and all(isinstance(x, str) for x in value) for value in (strengths, risks)):
        raise ValueError("Fortalezas y riesgos deben ser listas de texto.")
    if not isinstance(recommendation, str) or not recommendation.strip():
        raise ValueError("Falta la recomendación del modelo.")
    return {
        "name": normalize_name(name),
        "eligibility": eligibility(mandatory),
        "overall_score": overall_score(mandatory, desirable),
        "mandatory": mandatory,
        "desirable": desirable,
        "strengths": strengths,
        "risks": risks,
        "recommendation": recommendation.strip(),
        "legal_notice": "Pendiente de validación manual: disponibilidad de marca, dominios, redes sociales y posibles conflictos comerciales.",
    }


def export_rows(evaluations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for evaluation in evaluations:
        rows.append({
            "Nombre": evaluation["name"], "Elegibilidad": evaluation["eligibility"],
            "Puntuación global": evaluation["overall_score"],
            **{f"{code} puntuación": value["score"] for code, value in evaluation["mandatory"].items()},
            **{f"{code} estado": value["status"] for code, value in evaluation["mandatory"].items()},
            **{f"{code} puntuación": value["score"] for code, value in evaluation["desirable"].items()},
            "Recomendación": evaluation["recommendation"],
        })
    return rows


def pretty_json(evaluations: list[dict[str, Any]]) -> str:
    return json.dumps(evaluations, ensure_ascii=False, indent=2)
