"""Streamlit UI for the AWS Documentation Assistant API."""

import os
import time

import httpx
import streamlit as st

DEFAULT_API = "http://127.0.0.1:8000"


def api_base() -> str:
    return st.session_state.get("api_base", os.getenv("API_BASE_URL", DEFAULT_API)).rstrip("/")


def get_client() -> httpx.Client:
    return httpx.Client(base_url=api_base(), timeout=60.0)


def fetch_health() -> dict | None:
    try:
        with get_client() as client:
            r = client.get("/health")
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        st.session_state["health_error"] = str(exc)
        return None


def start_job(reindex: bool) -> dict | None:
    path = "/ingestion/reindex" if reindex else "/ingestion/start"
    body: dict = {}
    if st.session_state.get("prefix", "").strip():
        body["prefix"] = st.session_state["prefix"].strip()
    if st.session_state.get("max_documents"):
        body["max_documents"] = int(st.session_state["max_documents"])

    try:
        with get_client() as client:
            r = client.post(path, json=body)
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        st.error(str(exc))
        return None


def fetch_job_status(job_id: str) -> dict | None:
    try:
        with get_client() as client:
            r = client.get("/ingestion/status", params={"job_id": job_id})
            r.raise_for_status()
            return r.json()
    except Exception as exc:
        st.error(str(exc))
        return None


st.set_page_config(
    page_title="AWS Docs Assistant",
    page_icon="📚",
    layout="wide",
)

st.title("AWS Documentation Assistant")
st.caption("Ingestion control · Agentic RAG chat (coming soon)")

with st.sidebar:
    st.header("Settings")
    st.session_state["api_base"] = st.text_input(
        "API base URL",
        value=st.session_state.get("api_base", os.getenv("API_BASE_URL", DEFAULT_API)),
    )
    if st.button("Check API health"):
        st.session_state.pop("health_error", None)
        st.rerun()

health = fetch_health()
if health:
    st.success(f"API online — index `{health.get('opensearch_index')}` · {health.get('embedding_provider')}")
elif st.session_state.get("health_error"):
    st.warning(f"API unreachable: {st.session_state['health_error']}")

tab_ingest, tab_chat = st.tabs(["Ingestion", "Chat"])

with tab_ingest:
    st.subheader("Run ingestion pipeline")
    st.markdown("S3 → parse → preprocess → chunk → embed → OpenSearch")

    col1, col2 = st.columns(2)
    with col1:
        st.session_state["prefix"] = st.text_input("S3 prefix (optional)", placeholder="lambda/guides/")
    with col2:
        max_doc_raw = st.text_input("Max documents (optional)", placeholder="100")
    st.session_state["max_documents"] = int(max_doc_raw) if max_doc_raw.strip().isdigit() else None

    btn1, btn2 = st.columns(2)
    with btn1:
        if st.button("Start ingestion", type="primary", disabled=not health):
            job = start_job(reindex=False)
            if job:
                st.session_state["job_id"] = job["job_id"]
                st.rerun()
    with btn2:
        if st.button("Reindex", disabled=not health):
            job = start_job(reindex=True)
            if job:
                st.session_state["job_id"] = job["job_id"]
                st.rerun()

    job_id = st.session_state.get("job_id")
    if job_id:
        st.divider()
        st.markdown(f"**Job ID:** `{job_id}`")

        if st.button("Refresh status"):
            st.rerun()

        status = fetch_job_status(job_id)
        if status:
            st.metric("Status", status.get("status", "—"))
            c1, c2, c3 = st.columns(3)
            c1.metric("Phase", status.get("phase") or "—")
            c2.metric("Documents", status.get("documents_processed", 0))
            c3.metric("Chunks indexed", status.get("chunks_indexed", 0))

            if status.get("errors"):
                st.error("Errors")
                for err in status["errors"]:
                    st.write(f"- {err}")

            if status.get("status") in ("pending", "running"):
                time.sleep(2)
                st.rerun()

with tab_chat:
    st.subheader("Ask AWS Docs")
    st.info("Retrieval and generation will be available after ingestion is configured.")
    st.chat_input("How does Lambda reserved concurrency work?", disabled=True)
