import base64
import os
import uuid
from urllib.parse import quote_plus

import requests
import streamlit as st

API = os.getenv("API_ENDPOINT", "http://localhost:8000")

st.set_page_config(
    page_title="QA Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========================= MODERN GLASSMORPHISM DARK THEME =========================
st.markdown("""
<style>
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }
    
    /* Global Dark Theme with Glassmorphism */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a0a3e 50%, #0f0f23 100%);
        color: #e2e8f0;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    .main > div {
        padding: 2rem 3rem !important;
        background: transparent;
    }
    
    /* Header - Animated Gradient */
    .big-title {
        font-size: 3.6rem !important;
        font-weight: 900;
        text-align: center;
        background: linear-gradient(135deg, #60a5fa, #a78bfa, #ec4899);
        background-size: 200% 200%;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
        letter-spacing: -1px;
        animation: gradientShift 8s ease infinite;
    }
    
    @keyframes gradientShift {
        0%, 100% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
    }
    
    .subtitle {
        text-align: center;
        font-size: 1.15rem;
        background: linear-gradient(90deg, #94a3b8, #cbd5e1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0.5rem 0 2.5rem 0;
        font-weight: 500;
        letter-spacing: 0.3px;
    }
    
    /* Glassmorphic Sidebar */
    section[data-testid="stSidebar"] {
        background: rgba(17, 24, 39, 0.7) !important;
        backdrop-filter: blur(10px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.1) !important;
    }
    
    section[data-testid="stSidebar"] .stMarkdown > p {
        color: #cbd5e1;
    }
    
    .sidebar-title {
        font-size: 1.5rem;
        font-weight: 800;
        color: #f0f9ff;
        text-align: center;
        margin-bottom: 1.5rem;
        padding: 1rem;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(139, 92, 246, 0.15));
        border: 1px solid rgba(96, 165, 250, 0.3);
        border-radius: 16px;
        backdrop-filter: blur(8px);
    }
    
    .progress-step {
        padding: 1rem;
        border-radius: 14px;
        margin: 0.6rem 0;
        font-size: 0.95rem;
        font-weight: 600;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        color: #e2e8f0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        background: rgba(31, 41, 55, 0.6);
        border: 1px solid rgba(75, 85, 99, 0.4);
        backdrop-filter: blur(8px);
        cursor: pointer;
    }
    
    .progress-step:hover {
        background: rgba(59, 130, 246, 0.15);
        border-color: rgba(96, 165, 250, 0.5);
        transform: translateX(4px);
    }
    
    .progress-step.completed {
        background: rgba(16, 185, 129, 0.15);
        border-color: rgba(16, 185, 129, 0.4);
        border-left: 4px solid #10b981;
    }
    
    .progress-step.in-progress {
        background: rgba(59, 130, 246, 0.2);
        border-color: rgba(96, 165, 250, 0.6);
        border-left: 4px solid #3b82f6;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.3);
    }
    
    .progress-step.pending {
        background: rgba(75, 85, 99, 0.3);
        border-color: rgba(107, 114, 128, 0.3);
        opacity: 0.7;
    }
    
    .step-icon {
        font-size: 1.3em;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.2));
    }
    
    .step-status {
        font-size: 0.85em;
        color: #cbd5e1;
        font-weight: 600;
    }
    
    /* Step Headers - Modern Design */
    .step-header {
        font-size: 2rem;
        font-weight: 800;
        color: #f9fafb;
        margin: 2.5rem 0 1.2rem 0;
        display: flex;
        align-items: center;
        gap: 0.75rem;
        padding-bottom: 1rem;
        border-bottom: 2px solid rgba(96, 165, 250, 0.3);
        letter-spacing: -0.5px;
    }
    
    /* Input Styling */
    .stTextInput > div > div > input {
        background-color: rgba(31, 41, 55, 0.7) !important;
        color: #e2e8f0 !important;
        border: 1.5px solid rgba(96, 165, 250, 0.3) !important;
        border-radius: 12px !important;
        padding: 0.75rem 1rem !important;
        font-size: 1rem !important;
        transition: all 0.3s ease !important;
        backdrop-filter: blur(8px) !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #3b82f6 !important;
        background-color: rgba(31, 41, 55, 0.9) !important;
        box-shadow: 0 0 20px rgba(59, 130, 246, 0.3) !important;
    }
    
    .stFileUploader {
        background-color: rgba(31, 41, 55, 0.7) !important;
        border: 2px dashed rgba(96, 165, 250, 0.4) !important;
        border-radius: 16px !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s ease !important;
    }
    
    .stFileUploader:hover {
        border-color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.1) !important;
    }
    
    .stExpander {
        background-color: rgba(31, 41, 55, 0.6) !important;
        border: 1px solid rgba(96, 165, 250, 0.3) !important;
        border-radius: 14px !important;
        margin: 0.8rem 0 !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s ease !important;
    }
    
    .stExpander:hover {
        border-color: #3b82f6 !important;
        background-color: rgba(59, 130, 246, 0.15) !important;
    }
    
    .stExpander > div > label {
        color: #e2e8f0 !important;
        font-weight: 600 !important;
    }
    
    .stCode {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border: 1px solid rgba(96, 165, 250, 0.2) !important;
        border-radius: 12px !important;
        backdrop-filter: blur(8px) !important;
    }
    
    /* Test Case Cards - Modern */
    .test-case-card {
        background: linear-gradient(135deg, rgba(31, 41, 55, 0.8), rgba(55, 65, 81, 0.6));
        border: 1.5px solid rgba(96, 165, 250, 0.3);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(8px);
        cursor: pointer;
    }
    
    .test-case-card:hover {
        border-color: #3b82f6;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(96, 165, 250, 0.1));
        transform: translateY(-2px);
        box-shadow: 0 8px 32px rgba(59, 130, 246, 0.2);
    }
    
    .test-case-id {
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa, #93c5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 1rem;
        margin-bottom: 0.5rem;
        letter-spacing: 0.5px;
    }
    
    .test-case-feature {
        font-size: 1.2rem;
        font-weight: 700;
        color: #f9fafb;
        margin-bottom: 0.8rem;
    }
    
    .test-case-scenario {
        color: #d1d5db;
        font-size: 0.95rem;
        margin: 0.5rem 0;
        line-height: 1.6;
    }
    
    .test-case-expected {
        color: #a1a5b3;
        font-size: 0.9rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(96, 165, 250, 0.2);
        font-style: italic;
    }
    
    .grounded-badge {
        display: inline-block;
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(34, 197, 94, 0.2));
        color: #10b981;
        padding: 0.4rem 0.8rem;
        border-radius: 8px;
        font-size: 0.75rem;
        font-weight: 700;
        margin-top: 0.5rem;
        margin-right: 0.5rem;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    
    /* Buttons - Modern Design */
    .stButton > button {
        height: 3.2em;
        border-radius: 14px;
        font-weight: 700;
        font-size: 1.05rem;
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        border: none;
        color: white;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        width: 100%;
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.3);
        letter-spacing: 0.3px;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(59, 130, 246, 0.4);
    }
    
    .stButton > button:active {
        transform: translateY(0);
        box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
    }
    
    .stButton > button:disabled {
        background: rgba(107, 114, 128, 0.5);
        opacity: 0.6;
        box-shadow: none;
    }
    
    /* Selection Counter */
    .selection-counter {
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.15));
        border: 1.5px solid rgba(59, 130, 246, 0.5);
        color: #93c5fd;
        padding: 1rem;
        border-radius: 14px;
        text-align: center;
        font-weight: 700;
        margin: 1.5rem 0;
        backdrop-filter: blur(8px);
        box-shadow: 0 4px 15px rgba(59, 130, 246, 0.1);
        font-size: 1.05rem;
    }
    
    /* Playback Panel */
    .playback-panel {
        width: 100%;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.9), rgba(30, 41, 59, 0.8));
        border: 1.5px solid rgba(96, 165, 250, 0.3);
        border-radius: 18px;
        padding: 1rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
    }
    
    .playback-panel img,
    .playback-panel video {
        width: 100%;
        max-height: 640px;
        border-radius: 14px;
        object-fit: contain;
        display: block;
        box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    
    .live-feed-pill {
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(96, 165, 250, 0.15));
        border: 1.5px solid rgba(59, 130, 246, 0.5);
        color: #93c5fd;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 700;
        margin-bottom: 1rem;
        backdrop-filter: blur(8px);
        animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Alerts & Info */
    .stAlert {
        border-radius: 14px;
        border: 1.5px solid rgba(96, 165, 250, 0.3) !important;
        background-color: rgba(31, 41, 55, 0.7) !important;
        backdrop-filter: blur(8px) !important;
    }
    
    .stSuccess {
        background: rgba(16, 185, 129, 0.15) !important;
        border-color: rgba(16, 185, 129, 0.4) !important;
        color: #86efac !important;
    }
    
    .stError {
        background: rgba(239, 68, 68, 0.15) !important;
        border-color: rgba(239, 68, 68, 0.4) !important;
        color: #fca5a5 !important;
    }
    
    .stWarning {
        background: rgba(245, 158, 11, 0.15) !important;
        border-color: rgba(245, 158, 11, 0.4) !important;
        color: #fcd34d !important;
    }
    
    .stInfo {
        background: rgba(59, 130, 246, 0.15) !important;
        border-color: rgba(59, 130, 246, 0.4) !important;
        color: #93c5fd !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: transparent;
        padding: 0.5rem;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    /* Divider */
    hr {
        border: none;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(96, 165, 250, 0.3), transparent);
        margin: 2rem 0;
    }
    
    /* Footer */
    footer {
        border-top: 1px solid rgba(96, 165, 250, 0.2);
        padding-top: 2rem;
    }
    
    /* Scrollbar Styling */
    ::-webkit-scrollbar {
        width: 10px;
        height: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(31, 41, 55, 0.5);
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, rgba(59, 130, 246, 0.5), rgba(139, 92, 246, 0.5));
        border-radius: 5px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #3b82f6, #8b5cf6);
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
st.markdown('<h1 class="big-title">QA Agent</h1>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">AI-powered QA • Ingest docs • Generate grounded tests • Export Selenium scripts</p>', unsafe_allow_html=True)

# ========================= ENHANCED SIDEBAR =========================
with st.sidebar:
    st.markdown("<div class='sidebar-title'>Workflow Progress</div>", unsafe_allow_html=True)
    
    # Calculate progress
    step1_complete = bool(docs_path and checkout_html)
    step2_complete = bool(kb_info)
    step3_complete = bool(test_cases)
    step4_complete = bool(latest_script)
    step5_complete = bool(validation_report or playback_result)

    completed_steps = sum([
        step1_complete,
        step2_complete,
        step3_complete,
        step4_complete,
        step5_complete,
    ])
    total_steps = 5
    progress = (completed_steps / total_steps) * 100 if total_steps else 0
    st.progress(progress / 100)
    st.caption(f"{progress:.0f}% Complete • {completed_steps}/{total_steps} steps")
    
    st.markdown("---")
    
    st.markdown(f"""
    <div class="progress-step {'completed' if step1_complete else 'in-progress' if 'docs_path' in st.session_state else 'pending'}">
        <span class="step-icon">1</span>
        <span style="flex: 1;">Ingest Files</span>
        <span class="step-status">{'✓' if step1_complete else '•' if 'docs_path' in st.session_state else '○'}</span>
    </div>
    <div class="progress-step {'completed' if step2_complete else 'in-progress' if step1_complete else 'pending'}">
        <span class="step-icon">2</span>
        <span style="flex: 1;">Build KB</span>
        <span class="step-status">{'✓' if step2_complete else '•' if step1_complete else '○'}</span>
    </div>
    <div class="progress-step {'completed' if step3_complete else 'in-progress' if step2_complete else 'pending'}">
        <span class="step-icon">3</span>
        <span style="flex: 1;">Generate Tests</span>
        <span class="step-status">{'✓' if step3_complete else '•' if step2_complete else '○'}</span>
    </div>
    <div class="progress-step {'completed' if step4_complete else 'in-progress' if step3_complete else 'pending'}">
        <span class="step-icon">4</span>
        <span style="flex: 1;">Export Script</span>
        <span class="step-status">{'✓' if step4_complete else '•' if step3_complete else '○'}</span>
    </div>
    <div class="progress-step {'completed' if step5_complete else 'in-progress' if step4_complete else 'pending'}">
        <span class="step-icon">5</span>
        <span style="flex: 1;">Validate & Playback</span>
        <span class="step-status">{'✓' if step5_complete else '•' if step4_complete else '○'}</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("**Tip:** Each step unlocks the next—no jumping around!")

# ========================= STEP 1 - Single Upload =========================
st.markdown('<div class="step-header">Step 1: Ingest All Files</div>', unsafe_allow_html=True)

col1, col2 = st.columns([2, 1])
with col1:
    st.markdown("**Upload docs + checkout.html at once** (PDF, MD, TXT, JSON)")
with col2:
    html_url = st.text_input(
        "Checkout HTML URL (optional)",
        value=st.session_state.get("checkout_html_url", ""),
        placeholder="http://localhost:3000/checkout",
    )

all_files = st.file_uploader(
    "Drop files here",
    accept_multiple_files=True,
    type=["pdf", "md", "txt", "json", "html"],
    label_visibility="collapsed"
)

if st.button("Process All Files", type="primary", width='stretch'):
    html_src = None
    html_bytes = None
    files = []

    # Prioritise uploaded checkout.html if present, else fall back to URL
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
                resp = requests.get(html_url_value, timeout=20)
                resp.raise_for_status()
                html_bytes = resp.content
                html_src = resp.text
                files.append(("files", ("checkout.html", html_bytes, "text/html")))
            except Exception as exc:
                st.error(f"❌ Failed to fetch HTML from URL: {exc}")
                html_bytes = None
        else:
            html_bytes = None

    other_files = []
    for f in all_files or []:
        if html_file and f.name.lower() == "checkout.html":
            continue
        other_files.append(("files", (f.name, f.getbuffer(), f.type or "application/octet-stream")))

    files.extend(other_files)

    if not files:
        st.error("Upload at least one document or provide a checkout HTML URL/file")
    elif not html_bytes:
        st.error("❌ Provide checkout.html via upload or a reachable URL")
    else:
        with st.spinner("🔄 Processing uploads..."):
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
            st.success("All files processed successfully!")
        else:
            st.error(f"❌ {r.text}")

# ========================= STEP 2 - Build KB =========================
if "docs_path" in st.session_state:
    st.markdown('<div class="step-header">Step 2: Build Knowledge Base</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([1.2, 4])
    with c1:
        if st.button("🔨 Build KB", type="secondary", width='stretch'):
            with st.spinner("🔄 Indexing documents..."):
                r = requests.post(f"{API}/build_kb", json={"docs_path": st.session_state.docs_path})
            if r.ok:
                st.session_state.kb_info = r.json()
                for key in ("test_cases", "latest_script", "validation_report", "script_ready", "playback_result", "selected_test_ids"):
                    st.session_state.pop(key, None)
                st.success("✅ Knowledge base indexed!")
            else:
                st.error(f"❌ {r.text}")
    with c2:
        if st.session_state.get("kb_info"):
            info = st.session_state.kb_info
            st.info(f"Indexed: **{info['total_chunks']} chunks** from **{info['total_documents']} docs**")

# ========================= STEP 3 - Generate Tests =========================
if st.session_state.get("kb_info"):
    st.markdown('<div class="step-header">Step 3: Generate Test Cases</div>', unsafe_allow_html=True)
    query = st.text_input(
        "Test query",
        placeholder="e.g., checkout validation with invalid payment inputs",
        value=st.session_state.get("last_query", ""),
        label_visibility="collapsed"
    )
    c1, c2 = st.columns([1.2, 4])
    with c1:
        if st.button("⚡ Generate Tests", type="primary", width='stretch'):
            with st.spinner("🤖 Generating test scenarios..."):
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
                st.success(f"Generated **{len(res['test_cases'])}** test cases!")
                st.rerun()
            else:
                st.error(f"❌ {r.text}")
    with c2:
        if st.session_state.get("test_cases"):
            st.info(f"**{len(st.session_state.test_cases)}** test cases ready")

    if test_cases:
        st.markdown("**Generated Test Cases**")
        option_labels = [f"{tc['id']} · {tc['feature'][:42]}" for tc in test_cases]
        id_by_label = {label: tc["id"] for label, tc in zip(option_labels, test_cases)}

        prior_selection = st.session_state.get("selected_test_ids", [])
        default_labels = [label for label, case_id in id_by_label.items() if case_id in prior_selection]

        selected_labels = st.multiselect(
            "Select cases to automate",
            options=option_labels,
            default=default_labels,
            help="Multiselect keeps the UI fast even with dozens of cases.",
            key="case_multiselect",
        )
        st.session_state.selected_test_ids = [id_by_label[label] for label in selected_labels]

        preview_map = {tc["id"]: tc for tc in test_cases}
        preview_default = st.session_state.get("preview_case_id") or (prior_selection[0] if prior_selection else test_cases[0]["id"])
        if preview_default not in preview_map:
            preview_default = test_cases[0]["id"]
        preview_choice = st.selectbox(
            "Preview details",
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
                <div class="test-case-id">ID: {preview_case['id']}</div>
                <div class="test-case-feature">{preview_case['feature']}</div>
                <div class="test-case-scenario"><strong>Scenario:</strong><br/>{preview_case['scenario']}</div>
                <div class="test-case-expected"><strong>Expected:</strong><br/>{preview_case['expected_result']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if preview_case.get("grounded_in"):
            st.markdown(f"<span class='grounded-badge'>Grounded in: {' • '.join(preview_case['grounded_in'])}</span>", unsafe_allow_html=True)

# ========================= STEP 4 - Generate Script =========================
if test_cases:
    st.markdown('<div class="step-header">Step 4: Export Selenium Script</div>', unsafe_allow_html=True)
    
    if not checkout_html:
        st.warning("checkout.html required — return to Step 1")

    selected = st.session_state.get("selected_test_ids", [])
    
    if selected:
        st.markdown(f"""
        <div class="selection-counter">
            {len(selected)} test case(s) selected for automation
        </div>
        """, unsafe_allow_html=True)

    can_run = bool(selected and checkout_html)

    if st.button("🔧 Generate Script", type="primary", width='stretch', disabled=not can_run):
        with st.spinner("🤖 Generating Selenium code..."):
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
            st.success("Selenium script generated! Proceed to Step 5 for validation & playback.")
        else:
            st.error(f"❌ {r.text}")

    if latest_script:
        st.markdown("**Generated Script Preview**")
        with st.expander("View Full Script", expanded=False):
            st.code(latest_script, language="python")
        
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "Download Script",
                latest_script,
                "selenium_tests.py",
                "text/x-python",
                key="download_latest_script",
                width='stretch'
            )
        with col2:
            st.markdown("[Continue to Step 5 →](#step5-anchor)", unsafe_allow_html=True)

# ========================= STEP 5 - Validate & Playback =========================
if latest_script and checkout_html:
    st.markdown('<div id="step5-anchor"></div>', unsafe_allow_html=True)
    st.markdown('<div class="step-header">Step 5: Validate & Playback</div>', unsafe_allow_html=True)
    st.markdown("**One-click validation + headless automation with GIF/MP4 recording**")

    action_col, status_col = st.columns([1.1, 5])
    
    with action_col:
        st.markdown("**Action**")
        if st.button("▶ Run Full Pipeline", type="primary", width='stretch'):
            if not docs_path:
                st.error("Upload files again to rehydrate the session.")
            else:
                run_id = str(uuid.uuid4())
                st.session_state["pending_run_id"] = run_id
                encoded_docs_path = quote_plus(docs_path)
                live_url = f"{API}/live_feed?docs_path={encoded_docs_path}&run_id={run_id}"
                st.session_state["live_feed_url"] = live_url
                st.info("Live feed streaming...")
                st.session_state.pop("validation_report", None)
                st.session_state.pop("playback_result", None)
                
                payload = {
                    "docs_path": docs_path,
                    "script": latest_script,
                    "html": checkout_html,
                }
                report = None
                with st.spinner("Validating locators..."):
                    try:
                        resp = requests.post(f"{API}/validate_selenium", json=payload, timeout=30)
                        if resp.ok:
                            report = resp.json()
                            st.session_state["validation_report"] = report
                            st.success("Validation complete!")
                        else:
                            st.error(f"Validation failed: {resp.text}")
                    except Exception as err:
                        st.error(f"Connection error: {err}")

                if report:
                    with st.spinner("Running automation & recording..."):
                        playback_payload = {
                            "docs_path": docs_path,
                            "script": latest_script,
                            "html": checkout_html,
                            "run_id": run_id,
                        }
                        playback_data = None
                        try:
                            resp = requests.post(f"{API}/run_selenium", json=playback_payload, timeout=300)
                            if resp.ok:
                                playback_data = resp.json()
                            else:
                                playback_data = resp.json() if resp.text else {"status": "error", "stderr": resp.text}
                                st.error(f"Playback failed: {resp.text}")
                        except Exception as err:
                            st.error(f"Playback error: {err}")

                        if playback_data:
                            st.session_state["playback_result"] = playback_data
                            st.session_state.pop("live_feed_url", None)
                            st.session_state.pop("pending_run_id", None)
                            st.success("Automation complete!")
                else:
                    st.session_state.pop("live_feed_url", None)
                    st.session_state.pop("pending_run_id", None)

    with status_col:
        st.markdown("**Preview**")
        live_feed_url = st.session_state.get("live_feed_url")
        playback = st.session_state.get("playback_result")

        if live_feed_url:
            st.markdown("<span class='live-feed-pill'>LIVE FEED</span>", unsafe_allow_html=True)
            try:
                st.markdown(
                    f"<div class='playback-panel'><img src='{live_feed_url}' alt='Live stream' /></div>",
                    unsafe_allow_html=True,
                )
            except Exception as err:
                st.warning(f"Live preview unavailable: {err}")

        if playback:
            status = playback.get("status")
            run_id = playback.get("run_id", "automation")
            mp4_base64 = playback.get("mp4_base64")
            gif_base64 = playback.get("gif_base64")
            
            if status == "ok":
                st.success("Automation successful!")
            else:
                st.warning("Automation completed with warnings—see logs below")

            if mp4_base64:
                st.markdown(
                    f"<div class='playback-panel'><video controls autoplay muted loop playsinline src='data:video/mp4;base64,{mp4_base64}'></video></div>",
                    unsafe_allow_html=True,
                )
                video_bytes = base64.b64decode(mp4_base64)
                st.download_button(
                    "Download Video (MP4)",
                    video_bytes,
                    file_name=f"{run_id}.mp4",
                    mime="video/mp4",
                    key="download_playback_mp4",
                    width='stretch'
                )
            elif gif_base64:
                st.markdown(
                    f"<div class='playback-panel'><img src='data:image/gif;base64,{gif_base64}' alt='Playback recording' /></div>",
                    unsafe_allow_html=True,
                )
                gif_bytes = base64.b64decode(gif_base64)
                st.download_button(
                    "Download Recording (GIF)",
                    gif_bytes,
                    file_name=f"{run_id}.gif",
                    mime="image/gif",
                    key="download_playback_gif",
                    width='stretch'
                )
            else:
                st.info("No recorded frames. Verify Chrome is installed and accessible.")

            if playback.get("stdout"):
                st.markdown("**Console Output**")
                st.code(playback.get("stdout"), language="text")

            if playback.get("stderr"):
                st.markdown("**Errors & Logs**")
                st.code(playback.get("stderr"), language="text")
            
            st.session_state.pop("live_feed_url", None)
            st.session_state.pop("pending_run_id", None)
        else:
            if not live_feed_url:
                st.info("Click 'Run Full Pipeline' to execute and record automation.")

        st.markdown("---")
        st.markdown("**Static Validation Results**")
        report = st.session_state.get("validation_report")
        if report:
            summary = report.get("summary", {})
            passed = summary.get("passed_locators", 0)
            total = summary.get("total_locators", 0)
            failed = summary.get("failed_locators", 0)
            skipped = summary.get("skipped_locators", 0)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Passed", f"{passed}/{total}", delta=None)
            with col2:
                st.metric("Failed", failed, delta=None)
            with col3:
                st.metric("Skipped", skipped, delta=None)
            with col4:
                status_badge = "OK" if summary.get("overall_status") == "ok" else "Issues"
                st.metric("Status", status_badge)

            locator_rows = report.get("locator_results", [])
            if locator_rows:
                st.markdown("**Locator Coverage**")
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
                st.markdown("**Page Structure**")
                check_table = []
                for c in html_checks:
                    check_table.append({
                        "Component": c["check"],
                        "Count": c["count"],
                        "Status": "OK" if c["status"] == "ok" else "Warning",
                        "Message": c["message"]
                    })
                st.dataframe(check_table, width='stretch', hide_index=True)

            st.caption("Validation checks selector syntax & HTML element existence without running a browser.")
        else:
            st.info("Validation results will appear after running the pipeline.")

# ========================= FOOTER =========================
st.markdown("---")
st.markdown("""
<div style="text-align: center; margin-top: 3rem; padding: 2rem; background: linear-gradient(135deg, rgba(59, 130, 246, 0.1), rgba(139, 92, 246, 0.1)); border-radius: 16px; border: 1px solid rgba(96, 165, 250, 0.2); backdrop-filter: blur(8px);">
    <h3 style="color: #f9fafb; margin-bottom: 0.5rem;">QA Agent</h3>
    <p style="color: #cbd5e1; font-size: 0.95rem; margin: 0;">
        Autonomous testing with AI • Grounded test generation • Real-time playback recording
    </p>
    <p style="color: #6b7280; font-size: 0.85rem; margin-top: 0.5rem;">Built for precision and efficiency</p>
</div>
""", unsafe_allow_html=True)