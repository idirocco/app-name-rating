# Brand Name Evaluator

A Streamlit MVP for comparing names for a global technology platform. It does not validate trademarks, domains, social media accounts, or commercial conflicts; those checks remain manual.

## Local setup

Requires Python 3.11+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY='…'
streamlit run app.py
```

You may also configure `OPENAI_API_KEY` in `.streamlit/secrets.toml` (this file is excluded from Git):

```toml
OPENAI_API_KEY = "…"
```

The configured model is `gpt-4o-mini`, and it is displayed as read-only information in the sidebar. Streamlit Community Cloud hosting is free, although LLM provider usage may incur charges.

## Deployment on Streamlit Community Cloud

1. Upload this folder to a private or public repository without including secrets.
2. Create an application in Streamlit Community Cloud and select `app.py` as the main file.
3. In **Advanced settings → Secrets**, add `OPENAI_API_KEY = "..."`.

## Scoring methodology

Eligibility is calculated locally: a required `FAIL` takes precedence over any score. If no failures are present and a `REVIEW` exists, the final result is `REVIEW`.

The overall score is also computed locally: 20% average of M2/D3, 20% M3, 20% average of M4/D6, 15% M1, 15% M5, and 10% D4. D1 and D2 are calculated deterministically; D1 is a heuristic estimate of Spanish pronunciation and flags uncertainty when relevant.

## History and limits

Each result is stored in `.data/evaluated_names.json` and displayed beneath the evaluator with its full details. This file is not versioned and contains no secrets. On Streamlit Community Cloud, storage may be ephemeral; download the JSON history for long-term retention or use external storage before relying on it across restarts.

The application accepts up to 5 names per submission and up to 20 new evaluations per browser session. Before calling the LLM, it checks each name against the JSON history without distinguishing case or spaces. If a match is found, it returns the saved result and does not consume API calls or session quota.
