# Evaluador de Nombres de Marca

MVP en Streamlit para comparar nombres de una plataforma tecnológica global. No hace comprobaciones de marca, dominios, redes sociales o conflictos comerciales: esas validaciones son siempre manuales.

## Inicio local

Requiere Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='…'
streamlit run app.py
```

También puede configurar `OPENAI_API_KEY` en `.streamlit/secrets.toml` (ese archivo está excluido de Git):

```toml
OPENAI_API_KEY = "…"
```

El modelo configurado es `gpt-4o-mini` y se muestra como información de solo lectura en la barra lateral. El alojamiento en Streamlit Community Cloud es gratuito, pero el uso del proveedor LLM puede tener coste.

## Despliegue en Streamlit Community Cloud

1. Suba esta carpeta a un repositorio privado o público, sin incluir claves.
2. Cree una aplicación en Streamlit Community Cloud y seleccione `app.py` como archivo principal.
3. En **Advanced settings → Secrets**, añada `OPENAI_API_KEY = "..."`.

## Diseño de puntuación

La elegibilidad se calcula localmente: un `FAIL` obligatorio gana sobre cualquier puntuación; si no hay fallos y existe un `REVIEW`, el resultado es `REVIEW`.

La puntuación global también se calcula localmente: 20% promedio de M2/D3, 20% M3, 20% promedio de M4/D6, 15% M1, 15% M5 y 10% D4. D1 y D2 se calculan de forma determinística; D1 es una estimación heurística de pronunciación española y avisa de incertidumbre cuando corresponde.

## Historial y límites

Cada resultado se guarda en `.data/evaluated_names.json` y aparece debajo del evaluador con su detalle. Este archivo no se versiona ni contiene claves. En Streamlit Community Cloud el disco puede ser efímero: descargue el historial JSON para conservación permanente o use almacenamiento externo antes de depender de ese historial entre reinicios.

La aplicación acepta hasta 5 nombres por envío y hasta 20 evaluaciones nuevas por sesión de navegador. Antes de llamar al LLM, busca cada nombre en el historial JSON sin distinguir mayúsculas o espacios. Si ya existe, muestra el resultado guardado y no consume API ni el límite de sesión.
