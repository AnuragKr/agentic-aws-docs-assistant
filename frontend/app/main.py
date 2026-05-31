"""AWS Documentation Assistant — Streamlit search UI."""

import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

_FRONTEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_FRONTEND_ROOT / ".env")

BACKEND_API_URL = (
    os.getenv("BACKEND_API_URL")
    or os.getenv("API_BASE_URL")
    or "http://127.0.0.1:8000"
).rstrip("/")
SEARCH_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT", "120"))
HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "10"))
READY_TIMEOUT = float(os.getenv("READY_TIMEOUT", "30"))

st.set_page_config(
    page_title="AWS Docs Assistant",
    page_icon="🔍",
    layout="wide",
)
st.title("AWS Documentation Assistant")
st.caption("Semantic search over ingested AWS documentation")

with st.sidebar:
    st.header("Search settings")
    top_k = st.slider("Top K results", min_value=1, max_value=20, value=5)
    service_filter = st.text_input("Filter by service (optional)", placeholder="Lambda")
    section_filter = st.text_input("Filter by section (optional)")
    st.info(
        "First backend startup downloads ML models (~1.1GB reranker). "
        "Wait for `warmup_complete` in backend logs before searching."
    )

query = st.text_input(
    "Search query",
    placeholder="How does Lambda concurrency work?",
)

col1, col2, col3 = st.columns(3)
with col1:
    search_clicked = st.button("Search", type="primary", use_container_width=True)
with col2:
    health_clicked = st.button("Health (fast)", use_container_width=True)
with col3:
    ready_clicked = st.button("Ready check", use_container_width=True)

if health_clicked:
    try:
        response = httpx.get(f"{BACKEND_API_URL}/health", timeout=HEALTH_TIMEOUT)
        response.raise_for_status()
        st.success(response.json())
    except httpx.TimeoutException:
        st.error(f"Backend health timed out after {HEALTH_TIMEOUT}s.")
    except httpx.HTTPError as exc:
        st.error(f"Backend unavailable: {exc}")

if ready_clicked:
    with st.spinner("Checking OpenSearch readiness..."):
        try:
            response = httpx.get(f"{BACKEND_API_URL}/health/ready", timeout=READY_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            if body.get("status") == "ok":
                st.success(body)
            else:
                st.warning(body)
        except httpx.TimeoutException:
            st.error(
                f"Ready check timed out after {READY_TIMEOUT}s. "
                "OpenSearch in ap-south-1 can be slow from your laptop."
            )
        except httpx.HTTPError as exc:
            st.error(f"Backend unavailable: {exc}")

if search_clicked:
    if not query.strip():
        st.warning("Please enter a search query.")
    else:
        payload: dict = {"query": query.strip(), "top_k": top_k}
        filters: dict = {}
        if service_filter.strip():
            filters["service"] = service_filter.strip()
        if section_filter.strip():
            filters["section"] = section_filter.strip()
        if filters:
            payload["filters"] = filters

        with st.spinner("Searching documentation (first search may take 1–2 min)..."):
            try:
                response = httpx.post(
                    f"{BACKEND_API_URL}/search",
                    json=payload,
                    timeout=SEARCH_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException:
                st.error(
                    f"Search timed out after {SEARCH_TIMEOUT}s. "
                    "If the backend is still downloading models, wait and retry."
                )
            except httpx.ConnectError:
                st.error(
                    f"Cannot reach backend at `{BACKEND_API_URL}`. "
                    "Ensure the API is running: `cd backend/src && uv run uvicorn main:app --host 0.0.0.0 --port 8000`"
                )
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text
                st.error(f"Search failed ({exc.response.status_code}): {detail}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
            else:
                results = data.get("results", [])
                st.subheader(f"Results for: {data.get('query', query)}")
                st.write(f"Found **{len(results)}** result(s)")

                if not results:
                    st.info("No matching chunks found. Try a different query or filters.")
                else:
                    for index, result in enumerate(results, start=1):
                        title = result.get("title") or "Untitled"
                        section = result.get("section") or "—"
                        subsection = result.get("subsection") or "—"
                        score = result.get("score", 0)
                        label = f"#{index} {result.get('service') or 'Doc'} · {title} (score: {score:.3f})"

                        with st.expander(label, expanded=index == 1):
                            st.markdown(f"**Service:** {result.get('service') or '—'}")
                            st.markdown(f"**Title:** {title}")
                            st.markdown(f"**Section:** {section}")
                            st.markdown(f"**Subsection:** {subsection}")
                            st.markdown(f"**Score:** `{score:.4f}`")

                            source_url = result.get("source_url")
                            if source_url:
                                st.markdown(f"**Source:** [{source_url}]({source_url})")

                            if result.get("chunk_summary"):
                                st.markdown(f"**Summary:** {result['chunk_summary']}")

                            st.markdown("**Content**")
                            st.write(result.get("content", ""))

st.divider()
st.caption(f"Backend: `{BACKEND_API_URL}`")
