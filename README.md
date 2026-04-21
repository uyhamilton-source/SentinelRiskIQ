# SentinelRiskIQ™ Compliance App

GitHub-ready Streamlit app for combined SOC 2 and HIPAA readiness scoring.

## Included
- `app.py` — Streamlit entrypoint
- `compliance_readiness.py` — scoring engine
- `pdf_report.py` — branded PDF report module
- `sample_combined_intake.csv` — sample intake file
- `INTAKE_TO_OUTPUT_MAPPING.txt` — scoring/mapping guide
- `requirements.txt`

## Run locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud
1. Create a new GitHub repository.
2. Upload all files from this package.
3. In Streamlit Cloud, deploy with `app.py` as the main file.
4. Optionally add secrets for login in Streamlit Cloud.

## Demo login fallback
- `admin`
- `admin123`
