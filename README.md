# QA-Agent-for-Test-Case-and-Script-Generation

An end-to-end QA assistant that ingests project documentation plus the `target.html` page, builds a grounded knowledge base, generates structured test plans, and turns selected cases into executable Selenium (Python) scripts.

### To Run:
Backend: uvicorn backend.app:app --host 0.0.0.0 --port 8000 --reload
Frontend: streamlit run frontend\streamlit_app.py