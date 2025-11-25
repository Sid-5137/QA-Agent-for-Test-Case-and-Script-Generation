import base64
import os
import uuid
from urllib.parse import quote_plus

import requests
import streamlit as st

API = os.getenv("API_ENDPOINT", "http://localhost:8000")
HTML_FETCH_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

st.set_page_config(
    page_title="QA Agent",
    page_icon="▪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========================= REFINED MINIMAL PROFESSIONAL THEME =========================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* Base Theme */
    .stApp {
        background: #0a0e1a;
        color: #f0f3f7;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        font-weight: 400;
    }
    
    .main > div {
        padding: 3rem 4rem !important;
        max-width: 1600px;
        margin: 0 auto;
    }
    
    /* Typography Hierarchy */
    .page-header {
        margin-bottom: 0.75rem;
    }
    
    .page-title {
        font-size: 2.25rem;
        font-weight: 700;
        color: #ffffff;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    
    .page-subtitle {
        font-size: 0.95rem;
        color: #b4bac7;
        font-weight: 400;
        letter-spacing: 0.01em;
        margin-bottom: 3rem;
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #0d1117 !important;
        border-right: 1px solid #1f2937 !important;
        padding: 2rem 1.5rem !important;
    }
    
    .sidebar-header {
        font-size: 0.75rem;
        font-weight: 600;
        color: #b4bac7;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 1.25rem;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #1f2937;
    }
    
    .workflow-step {
        display: flex;
        align-items: center;
        gap: 0.875rem;
        padding: 0.875rem 1rem;
        margin: 0.375rem 0;
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        transition: all 0.2s ease;
        cursor: default;
    }
    
    .workflow-step:hover {
        background: #1c2128;
        border-color: #30363d;
    }
    
    .workflow-step.completed {
        background: #0d1117;
        border-color: #238636;
        border-left-width: 3px;
    }
    
    .workflow-step.active {
        background: #0d1117;
        border-color: #1f6feb;
        border-left-width: 3px;
    }
    
    .workflow-step.pending {
        opacity: 0.5;
    }
    
    .step-number {
        font-size: 0.75rem;
        font-weight: 600;
        color: #b4bac7;
        min-width: 1.5rem;
        font-variant-numeric: tabular-nums;
    }
    
    .workflow-step.completed .step-number {
        color: #3fb950;
    }
    
    .workflow-step.active .step-number {
        color: #58a6ff;
    }
    
    .step-label {
        flex: 1;
        font-size: 0.875rem;
        font-weight: 500;
        color: #e4e7ec;
    }
    
    .step-indicator {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #30363d;
    }
    
    .workflow-step.completed .step-indicator {
        background: #3fb950;
    }
    
    .workflow-step.active .step-indicator {
        background: #58a6ff;
        box-shadow: 0 0 8px rgba(88, 166, 255, 0.5);
    }
    
    .progress-stats {
        font-size: 0.75rem;
        color: #9ca3af;
        margin-top: 1rem;
        text-align: center;
        font-variant-numeric: tabular-nums;
    }
    
    /* Section Headers */
    .section-header {
        font-size: 1.125rem;
        font-weight: 600;
        color: #f9fafb;
        margin: 2.5rem 0 1.25rem 0;
        padding-bottom: 0.75rem;
        border-bottom: 1px solid #21262d;
        letter-spacing: -0.01em;
    }
    
    .section-description {
        font-size: 0.875rem;
        color: #b4bac7;
        margin-bottom: 1.5rem;
        line-height: 1.6;
    }
    
    /* Form Elements */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        background-color: #0d1117 !important;
        color: #f0f3f7 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        padding: 0.625rem 0.875rem !important;
        font-size: 0.875rem !important;
        font-weight: 400 !important;
        transition: all 0.15s ease !important;
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1f6feb !important;
        background-color: #161b22 !important;
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.1) !important;
    }
    
    .stTextInput > div > div > input::placeholder,
    .stTextArea > div > div > textarea::placeholder {
        color: #8b92a7 !important;
    }
    
    /* File Uploader */
    .stFileUploader {
        background-color: #0d1117 !important;
        border: 1px dashed #30363d !important;
        border-radius: 6px !important;
        padding: 1.5rem !important;
        transition: all 0.2s ease !important;
    }
    
    .stFileUploader:hover {
        border-color: #58a6ff !important;
        background-color: #161b22 !important;
    }
    
    .stFileUploader > div {
        color: #b4bac7 !important;
    }
    
    /* Buttons */
    .stButton > button {
        height: 2.5rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
        background: #238636;
        border: 1px solid #2ea043;
        color: #ffffff;
        transition: all 0.15s ease;
        width: 100%;
        letter-spacing: 0.005em;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    .stButton > button:hover {
        background: #2ea043;
        border-color: #3fb950;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
    }
    
    .stButton > button:active {
        background: #26a148;
        transform: translateY(0);
    }
    
    .stButton > button[kind="secondary"] {
        background: #21262d;
        border-color: #30363d;
        color: #e4e7ec;
    }
    
    .stButton > button[kind="secondary"]:hover {
        background: #30363d;
        border-color: #484f58;
    }
    
    .stButton > button:disabled {
        background: #21262d;
        border-color: #30363d;
        color: #6e7681;
        opacity: 0.6;
        cursor: not-allowed;
    }
    
    /* Download Button */
    .stDownloadButton > button {
        height: 2.5rem;
        border-radius: 6px;
        font-weight: 500;
        font-size: 0.875rem;
        background: #0d1117;
        border: 1px solid #30363d;
        color: #e4e7ec;
        transition: all 0.15s ease;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
    }
    
    .stDownloadButton > button:hover {
        background: #161b22;
        border-color: #58a6ff;
        color: #58a6ff;
    }
    
    /* Multiselect */
    .stMultiSelect > div > div {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
    }
    
    .stMultiSelect [data-baseweb="tag"] {
        background-color: #1f6feb !important;
        border-radius: 4px !important;
        font-size: 0.75rem !important;
        padding: 0.25rem 0.5rem !important;
    }
    
    /* Selectbox */
    .stSelectbox > div > div {
        background-color: #0d1117 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        color: #f0f3f7 !important;
    }
    
    .stSelectbox [data-baseweb="select"] {
        color: #f0f3f7 !important;
    }
    
    /* Test Case Cards */
    .test-case-card {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1.25rem;
        margin: 0.75rem 0;
        transition: all 0.2s ease;
    }
    
    .test-case-card:hover {
        border-color: #30363d;
        background: #161b22;
    }
    
    .test-case-meta {
        font-size: 0.75rem;
        font-weight: 600;
        color: #58a6ff;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .test-case-title {
        font-size: 0.95rem;
        font-weight: 600;
        color: #f9fafb;
        margin-bottom: 0.75rem;
        line-height: 1.4;
    }
    
    .test-case-content {
        font-size: 0.875rem;
        color: #b4bac7;
        line-height: 1.6;
        margin: 0.5rem 0;
    }
    
    .test-case-label {
        font-weight: 500;
        color: #e4e7ec;
    }
    
    .test-case-expected {
        font-size: 0.875rem;
        color: #9ca3af;
        margin-top: 0.875rem;
        padding-top: 0.875rem;
        border-top: 1px solid #21262d;
        font-style: italic;
    }
    
    .grounded-tag {
        display: inline-block;
        background: rgba(35, 134, 54, 0.15);
        color: #3fb950;
        padding: 0.25rem 0.5rem;
        border-radius: 4px;
        font-size: 0.7rem;
        font-weight: 600;
        margin-top: 0.5rem;
        margin-right: 0.375rem;
        border: 1px solid rgba(35, 134, 54, 0.3);
        letter-spacing: 0.02em;
    }
    
    /* Selection Counter */
    .selection-info {
        background: rgba(31, 111, 235, 0.08);
        border: 1px solid rgba(31, 111, 235, 0.2);
        color: #58a6ff;
        padding: 0.875rem 1.125rem;
        border-radius: 6px;
        text-align: center;
        font-weight: 500;
        margin: 1.25rem 0;
        font-size: 0.875rem;
        font-variant-numeric: tabular-nums;
    }
    
    /* Expander */
    .stExpander {
        background-color: #0d1117 !important;
        border: 1px solid #21262d !important;
        border-radius: 6px !important;
        margin: 0.75rem 0 !important;
    }
    
    .stExpander:hover {
        border-color: #30363d !important;
    }
    
    .stExpander summary {
        color: #e4e7ec !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
    }
    
    /* Code Block */
    .stCodeBlock {
        background-color: #0d1117 !important;
        border: 1px solid #21262d !important;
        border-radius: 6px !important;
        font-size: 0.8125rem !important;
    }
    
    /* Playback Panel */
    .playback-container {
        width: 100%;
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 1.5rem;
    }
    
    .playback-container img,
    .playback-container video {
        width: 100%;
        max-height: 600px;
        border-radius: 4px;
        object-fit: contain;
        display: block;
        background: #000000;
    }
    
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: rgba(31, 111, 235, 0.12);
        border: 1px solid rgba(31, 111, 235, 0.25);
        color: #58a6ff;
        padding: 0.375rem 0.75rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-bottom: 0.875rem;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }
    
    .status-indicator {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #58a6ff;
        animation: pulse-glow 2s ease-in-out infinite;
    }
    
    @keyframes pulse-glow {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 6px !important;
        border: 1px solid #30363d !important;
        background-color: #161b22 !important;
        font-size: 0.875rem !important;
    }
    
    .stSuccess {
        background: rgba(35, 134, 54, 0.08) !important;
        border-color: rgba(35, 134, 54, 0.3) !important;
        color: #3fb950 !important;
    }
    
    .stError {
        background: rgba(248, 81, 73, 0.08) !important;
        border-color: rgba(248, 81, 73, 0.3) !important;
        color: #f85149 !important;
    }
    
    .stWarning {
        background: rgba(187, 128, 9, 0.08) !important;
        border-color: rgba(187, 128, 9, 0.3) !important;
        color: #d29922 !important;
    }
    
    .stInfo {
        background: rgba(31, 111, 235, 0.08) !important;
        border-color: rgba(31, 111, 235, 0.25) !important;
        color: #58a6ff !important;
    }
    
    /* Metrics */
    .metric-container {
        background: #0d1117;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 1rem;
        text-align: center;
    }
    
    .metric-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #f9fafb;
        margin-bottom: 0.25rem;
        font-variant-numeric: tabular-nums;
    }
    
    .metric-label {
        font-size: 0.75rem;
        color: #b4bac7;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* DataFrame */
    .stDataFrame {
        border: 1px solid #21262d !important;
        border-radius: 6px !important;
        overflow: hidden !important;
    }
    
    /* Progress Bar */
    .stProgress > div > div {
        background-color: #161b22 !important;
        border-radius: 4px !important;
    }
    
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #1f6feb, #58a6ff) !important;
        border-radius: 4px !important;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: #21262d;
        margin: 2.5rem 0;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.25rem;
        background-color: transparent;
        border-bottom: 1px solid #21262d;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        font-weight: 500;
        font-size: 0.875rem;
        color: #b4bac7;
        padding: 0.625rem 1rem;
    }
    
    .stTabs [data-baseweb="tab"]:hover {
        background: #161b22;
        color: #e4e7ec;
    }
    
    .stTabs [aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom: 2px solid #1f6feb !important;
    }
    
    /* Footer */
    .app-footer {
        text-align: center;
        margin-top: 4rem;
        padding: 2rem 0;
        border-top: 1px solid #21262d;
    }
    
    .footer-title {
        font-size: 0.875rem;
        font-weight: 600;
        color: #e4e7ec;
        margin-bottom: 0.375rem;
    }
    
    .footer-description {
        font-size: 0.8125rem;
        color: #9ca3af;
        line-height: 1.5;
    }
    
    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    ::-webkit-scrollbar-track {
        background: #0d1117;
    }
    
    ::-webkit-scrollbar-thumb {
        background: #30363d;
        border-radius: 4px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: #484f58;
    }
    
    /* Caption Text */
    .stCaption {
        color: #9ca3af !important;
        font-size: 0.8125rem !important;
    }
    
    /* Labels */
    label {
        color: #e4e7ec !important;
        font-weight: 500 !important;
    }
    
    /* Markdown text */
    .stMarkdown {
        color: #e4e7ec;
    }
</style>
""", unsafe_allow_html=True)

# Centralized session lookups
docs_path = st.session_state.get("docs_path")
checkout_html = st.session_state.get("checkout_html")
kb_info = st.session_state.get("kb_info")
test_cases = st.session_state.get("test_cases", [])
latest_script = st.session_state.get("latest_script")
validation_report = st.session_state.get("validation_report")
playback_result = st.session_state.get("playback_result")

# ========================= HEADER =========================
st.markdown('<div class="page-header">', unsafe_allow_html=True)
st.markdown('<div class="page-title">QA Agent</div>', unsafe_allow_html=True)
st.markdown('<div class="page-subtitle">Automated test generation and validation system</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ========================= SIDEBAR =========================
with st.sidebar:
    st.markdown("<div class='sidebar-header'>Workflow Progress</div>", unsafe_allow_html=True)
    
    # Calculate progress
    step1_complete = bool(docs_path and checkout_html)
    step2_complete = bool(kb_info)
    step3_complete = bool(test_cases)
    step4_complete = bool(latest_script)
    step5_complete = bool(validation_report or playback_result)

    completed_steps = sum([step1_complete, step2_complete, step3_complete, step4_complete, step5_complete])
    total_steps = 5
    progress = (completed_steps / total_steps) * 100 if total_steps else 0
    
    st.progress(progress / 100)
    st.markdown(f"<div class='progress-stats'>{completed_steps} of {total_steps} completed</div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Step 1
    step1_status = "completed" if step1_complete else ("active" if not step1_complete else "pending")
    st.markdown(f"""
    <div class="workflow-step {step1_status}">
        <span class="step-number">01</span>
        <span class="step-label">Ingest Files</span>
        <span class="step-indicator"></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 2
    step2_status = "completed" if step2_complete else ("active" if step1_complete and not step2_complete else "pending")
    st.markdown(f"""
    <div class="workflow-step {step2_status}">
        <span class="step-number">02</span>
        <span class="step-label">Build Knowledge Base</span>
        <span class="step-indicator"></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 3
    step3_status = "completed" if step3_complete else ("active" if step2_complete and not step3_complete else "pending")
    st.markdown(f"""
    <div class="workflow-step {step3_status}">
        <span class="step-number">03</span>
        <span class="step-label">Generate Test Cases</span>
        <span class="step-indicator"></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 4
    step4_status = "completed" if step4_complete else ("active" if step3_complete and not step4_complete else "pending")
    st.markdown(f"""
    <div class="workflow-step {step4_status}">
        <span class="step-number">04</span>
        <span class="step-label">Export Script</span>
        <span class="step-indicator"></span>
    </div>
    """, unsafe_allow_html=True)
    
    # Step 5
    step5_status = "completed" if step5_complete else ("active" if step4_complete and not step5_complete else "pending")
    st.markdown(f"""
    <div class="workflow-step {step5_status}">
        <span class="step-number">05</span>
        <span class="step-label">Validate & Execute</span>
        <span class="step-indicator"></span>
    </div>
    """, unsafe_allow_html=True)

# ========================= STEP 1 =========================
st.markdown('<div class="section-header">Step 1: Ingest Documentation</div>', unsafe_allow_html=True)
st.markdown('<div class="section-description">Upload project documentation with target page HTML/ paste the target web page for analysis</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    all_files = st.file_uploader(
        "Documentation Files",
        accept_multiple_files=True,
        type=["pdf", "md", "txt", "json", "html"],
        help="Supported formats: PDF, Markdown, Text, JSON, HTML"
    )
with col2:
    html_url = st.text_input(
        "Checkout URL",
        value=st.session_state.get("checkout_html_url", ""),
        placeholder="Paste the link to your target.html",
        help="Optional: Provide URL instead of file upload"
    )

if st.button("Process Files", type="primary"):
    html_src = None
    html_bytes = None
    files = []

    # Handle HTML source
    html_file = next((f for f in all_files or [] if f.name.lower() == "checkout.html"), None)
    if html_file:
        html_bytes = html_file.getvalue()
        html_src = html_bytes.decode("utf-8", errors="ignore")
        files.append(("files", ("checkout.html", html_bytes, "text/html")))
        html_url_value = ""
    else:
        html_url_value = (html_url or "").strip()
        if html_url_value:
            try:
                resp = requests.get(html_url_value, timeout=20, headers=HTML_FETCH_HEADERS)
                resp.raise_for_status()
                html_bytes = resp.content
                html_src = resp.text
                files.append(("files", ("checkout.html", html_bytes, "text/html")))
            except Exception as exc:
                st.error(f"Failed to fetch HTML from URL: {exc}")
                html_bytes = None
        else:
            html_bytes = None

    # Handle other files
    other_files = []
    for f in all_files or []:
        if html_file and f.name.lower() == "checkout.html":
            continue
        other_files.append(("files", (f.name, f.getbuffer(), f.type or "application/octet-stream")))

    files.extend(other_files)

    if not files:
        st.error("Please upload at least one document or provide a checkout HTML URL")
    elif not html_bytes:
        st.error("Checkout HTML is required via file upload or URL")
    else:
        with st.spinner("Processing files..."):
            r = requests.post(f"{API}/upload_files", files=files)
        if r.ok:
            data = r.json()
            st.session_state.docs_path = data["docs_path"]
            st.session_state.checkout_html = html_src
            if html_url_value:
                st.session_state.checkout_html_url = html_url_value
            else:
                st.session_state.pop("checkout_html_url", None)
            for key in ("kb_info", "test_cases", "latest_script", "validation_report", "script_ready", "last_query", "playback_result", "selected_test_ids"):
                st.session_state.pop(key, None)
            st.success("Files processed successfully")
            st.rerun()
        else:
            st.error(f"Processing failed: {r.text}")

# ========================= STEP 2 =========================
if "docs_path" in st.session_state:
    st.markdown('<div class="section-header">Step 2: Build Knowledge Base</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-description">Index documentation for intelligent test generation</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Build Knowledge Base", type="secondary"):
            with st.spinner("Indexing documents..."):
                r = requests.post(f"{API}/build_kb", json={"docs_path": st.session_state.docs_path})
            if r.ok:
                st.session_state.kb_info = r.json()
                for key in ("test_cases", "latest_script", "validation_report", "script_ready", "playback_result", "selected_test_ids"):
                    st.session_state.pop(key, None)
                st.success("Knowledge base created successfully")
                st.rerun()
            else:
                st.error(f"Indexing failed: {r.text}")
    
    with col2:
        if st.session_state.get("kb_info"):
            info = st.session_state.kb_info
            st.info(f"Indexed {info['total_chunks']} chunks from {info['total_documents']} documents")

# ========================= STEP 3 =========================
if st.session_state.get("kb_info"):
    st.markdown('<div class="section-header">Step 3: Generate Test Cases</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-description">Define test scenarios using natural language queries</div>', unsafe_allow_html=True)
    
    query = st.text_input(
        "Test Scenario Query",
        placeholder="Example: Validate checkout flow with invalid payment methods",
        value=st.session_state.get("last_query", ""),
        help="Describe the test scenarios you want to generate"
    )
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("Generate Test Cases", type="primary"):
            with st.spinner("Generating test scenarios..."):
                r = requests.post(f"{API}/generate_tests", json={
                    "docs_path": st.session_state.docs_path,
                    "query": query,
                    "rebuild": False
                })
            if r.ok:
                res = r.json()
                st.session_state.test_cases = res["test_cases"]
                st.session_state.last_query = query
                for key in ("latest_script", "validation_report", "script_ready", "playback_result", "selected_test_ids"):
                    st.session_state.pop(key, None)
                st.success(f"Generated {len(res['test_cases'])} test cases")
                st.rerun()
            else:
                st.error(f"Generation failed: {r.text}")
    
    with col2:
        if st.session_state.get("test_cases"):
            st.info(f"{len(st.session_state.test_cases)} test cases available for review")

    if test_cases:
        st.markdown("**Test Case Selection**")
        
        option_labels = [f"{tc['id']} · {tc['feature'][:50]}" for tc in test_cases]
        id_by_label = {label: tc["id"] for label, tc in zip(option_labels, test_cases)}

        prior_selection = st.session_state.get("selected_test_ids", [])
        default_labels = [label for label, case_id in id_by_label.items() if case_id in prior_selection]

        selected_labels = st.multiselect(
            "Select test cases to automate",
            options=option_labels,
            default=default_labels,
            help="Choose one or more test cases for script generation",
            key="case_multiselect",
        )
        st.session_state.selected_test_ids = [id_by_label[label] for label in selected_labels]

        # Preview section
        preview_map = {tc["id"]: tc for tc in test_cases}
        preview_default = st.session_state.get("preview_case_id") or (prior_selection[0] if prior_selection else test_cases[0]["id"])
        if preview_default not in preview_map:
            preview_default = test_cases[0]["id"]
            
        preview_choice = st.selectbox(
            "Preview Test Case",
            options=list(preview_map.keys()),
            index=list(preview_map.keys()).index(preview_default),
            format_func=lambda cid: f"{cid} · {preview_map[cid]['feature']}",
            key="preview_case_select",
        )
        st.session_state["preview_case_id"] = preview_choice

        preview_case = preview_map[preview_choice]
        st.markdown(
            f"""
            <div class="test-case-card">
                <div class="test-case-meta">{preview_case['id']}</div>
                <div class="test-case-title">{preview_case['feature']}</div>
                <div class="test-case-content">
                    <span class="test-case-label">Scenario:</span> {preview_case['scenario']}
                </div>
                <div class="test-case-expected">
                    <span class="test-case-label">Expected Result:</span> {preview_case['expected_result']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if preview_case.get("grounded_in"):
            tags_html = "".join([f"<span class='grounded-tag'>{src}</span>" for src in preview_case['grounded_in']])
            st.markdown(tags_html, unsafe_allow_html=True)

# ========================= STEP 4 =========================
if test_cases:
    st.markdown('<div class="section-header">Step 4: Export Selenium Script</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-description">Generate executable Selenium automation code</div>', unsafe_allow_html=True)
    
    if not checkout_html:
        st.warning("Checkout HTML required. Please return to Step 1 to upload the file.")

    selected = st.session_state.get("selected_test_ids", [])
    
    if selected:
        st.markdown(f"""
        <div class="selection-info">
            {len(selected)} test case{"s" if len(selected) != 1 else ""} selected for script generation
        </div>
        """, unsafe_allow_html=True)

    can_run = bool(selected and checkout_html)

    if st.button("Generate Selenium Script", type="primary", disabled=not can_run):
        with st.spinner("Generating automation code..."):
            selected_cases = [tc for tc in test_cases if tc['id'] in selected]
            r = requests.post(f"{API}/generate_selenium", json={
                "docs_path": docs_path,
                "query": st.session_state.get("last_query", ""),
                "html": checkout_html,
                "selected_ids": selected,
                "test_cases": selected_cases
            })
        if r.ok:
            script = r.json()["selenium_script"]
            st.session_state["latest_script"] = script
            latest_script = script
            st.session_state["script_ready"] = True
            st.session_state.pop("validation_report", None)
            st.session_state.pop("playback_result", None)
            st.success("Selenium script generated successfully")
            st.rerun()
        else:
            st.error(f"Generation failed: {r.text}")

    if latest_script:
        with st.expander("View Generated Script", expanded=False):
            st.code(latest_script, language="python")
        
        st.download_button(
            "Download Script",
            latest_script,
            "selenium_tests.py",
            "text/x-python",
            key="download_latest_script",
        )

# ========================= STEP 5 =========================
if latest_script and checkout_html:
    st.markdown('<div class="section-header">Step 5: Validate & Execute</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-description">Run validation checks and execute automated tests with recording</div>', unsafe_allow_html=True)
    selected_ids = st.session_state.get("selected_test_ids", [])

    if st.button("Execute Validation Pipeline", type="primary"):
        if not docs_path:
            st.error("Session expired. Please upload files again.")
        else:
            run_id = str(uuid.uuid4())
            st.session_state["pending_run_id"] = run_id
            encoded_docs_path = quote_plus(docs_path)
            live_url = f"{API}/live_feed?docs_path={encoded_docs_path}&run_id={run_id}"
            st.session_state["live_feed_url"] = live_url
            st.session_state.pop("validation_report", None)
            st.session_state.pop("playback_result", None)
            
            payload = {
                "docs_path": docs_path,
                "script": latest_script,
                "html": checkout_html,
            }
            report = None
            with st.spinner("Validating script..."):
                try:
                    resp = requests.post(f"{API}/validate_selenium", json=payload, timeout=30)
                    if resp.ok:
                        report = resp.json()
                        st.session_state["validation_report"] = report
                        st.success("Validation completed")
                    else:
                        st.error(f"Validation failed: {resp.text}")
                except Exception as err:
                    st.error(f"Connection error: {err}")

            if report:
                with st.spinner("Executing automation..."):
                    playback_payload = {
                        "docs_path": docs_path,
                        "script": latest_script,
                        "html": checkout_html,
                        "run_id": run_id,
                        "selected_ids": selected_ids,
                    }
                    playback_data = None
                    try:
                        resp = requests.post(f"{API}/run_selenium", json=playback_payload, timeout=300)
                        if resp.ok:
                            playback_data = resp.json()
                        else:
                            playback_data = resp.json() if resp.text else {"status": "error", "stderr": resp.text}
                            st.error(f"Execution failed: {resp.text}")
                    except Exception as err:
                        st.error(f"Execution error: {err}")

                    if playback_data:
                        st.session_state["playback_result"] = playback_data
                        st.session_state.pop("live_feed_url", None)
                        st.session_state.pop("pending_run_id", None)
                        st.success("Automation completed")
                        st.rerun()
            else:
                st.session_state.pop("live_feed_url", None)
                st.session_state.pop("pending_run_id", None)

    # Live Feed Display
    live_feed_url = st.session_state.get("live_feed_url")
    if live_feed_url:
        st.markdown("""
        <div class="status-badge">
            <span class="status-indicator"></span>
            <span>Live Execution</span>
        </div>
        """, unsafe_allow_html=True)
        try:
            st.markdown(
                f"<div class='playback-container'><img src='{live_feed_url}' alt='Live execution feed' /></div>",
                unsafe_allow_html=True,
            )
        except Exception as err:
            st.warning(f"Live preview unavailable: {err}")

    # Playback Results
    playback = st.session_state.get("playback_result")
    if playback:
        status = playback.get("status")
        run_id = playback.get("run_id", "automation")
        mp4_base64 = playback.get("mp4_base64")
        gif_base64 = playback.get("gif_base64")
        
        if status == "ok":
            st.success("Automation executed successfully")
        else:
            st.warning("Automation completed with warnings")

        if mp4_base64:
            st.markdown("**Execution Recording**")
            st.markdown(
                f"<div class='playback-container'><video controls autoplay muted loop playsinline src='data:video/mp4;base64,{mp4_base64}'></video></div>",
                unsafe_allow_html=True,
            )
            video_bytes = base64.b64decode(mp4_base64)
            st.download_button(
                "Download Video Recording",
                video_bytes,
                file_name=f"{run_id}.mp4",
                mime="video/mp4",
                key="download_playback_mp4",
            )
        elif gif_base64:
            st.markdown("**Execution Recording**")
            st.markdown(
                f"<div class='playback-container'><img src='data:image/gif;base64,{gif_base64}' alt='Execution recording' /></div>",
                unsafe_allow_html=True,
            )
            gif_bytes = base64.b64decode(gif_base64)
            st.download_button(
                "Download GIF Recording",
                gif_bytes,
                file_name=f"{run_id}.gif",
                mime="image/gif",
                key="download_playback_gif",
            )
        else:
            st.info("No recording available. Verify Chrome installation.")


        if playback.get("stdout"):
            with st.expander("Execution Log"):
                st.code(playback.get("stdout"), language="text")

        if playback.get("stderr"):
            with st.expander("Error Log"):
                st.code(playback.get("stderr"), language="text")

    # Validation Report
    st.markdown("**Validation Report**")
    report = st.session_state.get("validation_report")
    if report:
        summary = report.get("summary", {})
        passed = summary.get("passed_locators", 0)
        total = summary.get("total_locators", 0)
        failed = summary.get("failed_locators", 0)
        skipped = summary.get("skipped_locators", 0)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Passed", f"{passed}/{total}")
        with col2:
            st.metric("Failed", failed)
        with col3:
            st.metric("Skipped", skipped)
        with col4:
            status_label = "Valid" if summary.get("overall_status") == "ok" else "Issues"
            st.metric("Status", status_label)

        locator_rows = report.get("locator_results", [])
        if locator_rows:
            st.markdown("**Locator Analysis**")
            st.dataframe(
                locator_rows,
                width='stretch',
                hide_index=True,
                column_config={
                    "by": "Strategy",
                    "value": "Selector",
                    "status": "Status",
                    "lineno": "Line"
                }
            )

        html_checks = report.get("html_checks", [])
        if html_checks:
            st.markdown("**Page Structure Checks**")
            check_table = []
            for c in html_checks:
                check_table.append({
                    "Component": c["check"],
                    "Count": c["count"],
                    "Status": "Valid" if c["status"] == "ok" else "Warning",
                    "Details": c["message"]
                })
            st.dataframe(check_table, width='stretch', hide_index=True)
    else:
        st.info("Validation results will appear after pipeline execution")

# ========================= FOOTER =========================
st.markdown("---")
st.markdown("""
<div class="app-footer">
    <div class="footer-title">QA Agent</div>
    <div class="footer-description">
        Intelligent test automation platform with document-grounded test generation and real-time validation
    </div>
</div>
""", unsafe_allow_html=True)
