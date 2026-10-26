from __future__ import annotations

import csv
import io

import streamlit as st

from evaluator import build_evaluation, export_rows, pretty_json
from llm import evaluate_with_llm, get_api_key

st.set_page_config(page_title="Evaluador de Nombres", page_icon="✦", layout="wide")
st.title("Evaluador de nombres de marca")
st.caption("Marco interno para comparar nombres de una plataforma tecnológica global.")
st.warning("Pendiente de validación manual: disponibilidad de marca, dominios, redes sociales y posibles conflictos comerciales.")

with st.sidebar:
    st.header("Configuración")
    model = st.text_input("Modelo LLM", value="gpt-4o-mini", help="Use un modelo compatible con salida JSON estructurada.")
    st.caption("La inferencia puede tener coste. La clave API nunca se muestra ni se guarda en esta aplicación.")

names_text = st.text_area("Nombres candidatos", placeholder="Ejemplo:\nNuvio\nVetra\nAurea", height=160, help="Introduzca un nombre por línea.")
extra_context = st.text_area("Contexto adicional (opcional)", placeholder="Ej.: queremos una impresión más premium o cercana.", height=90)


def label_status(status: str) -> str:
    return {"PASS": "APTO", "FAIL": "NO APTO", "REVIEW": "REVISAR"}[status]


def show_criteria(title: str, criteria: dict) -> None:
    st.subheader(title)
    rows = []
    for code, item in criteria.items():
        row = {"Código": code, "Criterio": item["criterion"], "Resultado": "Puntuado", "Puntuación": item["score"], "Explicación": item["reasoning"]}
        if "status" in item:
            row.update({"Resultado": label_status(item["status"]), "Confianza": {"LOW": "Baja", "MEDIUM": "Media", "HIGH": "Alta"}[item["confidence"]]})
        rows.append(row)
    st.dataframe(rows, use_container_width=True, hide_index=True)


if st.button("Evaluar nombres", type="primary"):
    names = list(dict.fromkeys(line.strip() for line in names_text.splitlines() if line.strip()))
    if not names:
        st.error("Introduzca al menos un nombre, uno por línea.")
    elif len(names) > 20:
        st.error("Para controlar el coste, evalúe como máximo 20 nombres por vez.")
    elif not (api_key := get_api_key(st.secrets)):
        st.error("No se encontró OPENAI_API_KEY. Añádala como variable de entorno o en los secretos de Streamlit.")
    else:
        evaluations = []
        progress = st.progress(0, text="Preparando evaluación…")
        try:
            for index, name in enumerate(names, start=1):
                progress.progress((index - 1) / len(names), text=f"Evaluando {name} ({index}/{len(names)})…")
                evaluations.append(build_evaluation(name, evaluate_with_llm(name, extra_context, model, api_key)))
            progress.progress(1.0, text="Evaluación completada.")
            st.session_state["evaluations"] = evaluations
        except Exception:
            progress.empty()
            st.error("No fue posible completar la evaluación. Revise el modelo, la clave y la conexión.")

evaluations = st.session_state.get("evaluations", [])
if evaluations:
    st.divider()
    if len(evaluations) > 1:
        st.subheader("Comparación")
        comparison = [{"Nombre": e["name"], "Elegibilidad": label_status(e["eligibility"]), "Puntuación global": e["overall_score"]} for e in evaluations]
        st.dataframe(comparison, use_container_width=True, hide_index=True)

    for evaluation in evaluations:
        with st.expander(f"{evaluation['name']} — {label_status(evaluation['eligibility'])} · {evaluation['overall_score']}/10", expanded=len(evaluations) == 1):
            left, right = st.columns(2)
            left.metric("Elegibilidad", label_status(evaluation["eligibility"]))
            right.metric("Puntuación global", f"{evaluation['overall_score']}/10")
            show_criteria("Criterios obligatorios", evaluation["mandatory"])
            show_criteria("Criterios deseables", evaluation["desirable"])
            st.subheader("Fortalezas")
            st.write("; ".join(evaluation["strengths"]) or "No se indicaron fortalezas.")
            st.subheader("Debilidades y riesgos")
            st.write("; ".join(evaluation["risks"]) or "No se indicaron riesgos.")
            st.subheader("Recomendación")
            st.write(evaluation["recommendation"])
            st.info(evaluation["legal_notice"])

    csv_buffer = io.StringIO()
    rows = export_rows(evaluations)
    writer = csv.DictWriter(csv_buffer, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    col1, col2 = st.columns(2)
    col1.download_button("Exportar CSV", csv_buffer.getvalue().encode("utf-8-sig"), "evaluacion_nombres.csv", "text/csv")
    col2.download_button("Exportar JSON", pretty_json(evaluations).encode("utf-8"), "evaluacion_nombres.json", "application/json")
