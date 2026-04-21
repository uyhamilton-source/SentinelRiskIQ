SentinelRiskIQ direct client-form upload package

What this version does:
- accepts a normal CSV or Control Intake workbook
- also accepts the client-friendly workbook
- if a client-friendly workbook is uploaded, the app reads the Client Form sheet
  and automatically builds backend Control Intake rows before scoring

Run:
1. pip install -r requirements.txt
2. streamlit run app.py
