"""AWS Documentation Assistant — search and RAG answer UI."""

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
GENERATION_TIMEOUT = float(os.getenv("GENERATION_TIMEOUT", "120"))
HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "10"))
READY_TIMEOUT = float(os.getenv("READY_TIMEOUT", "30"))

st.set_page_config(
    page_title="AWS Docs Assistant",
    page_icon="🔍",
    layout="wide",
)
st.title("AWS Documentation Assistant")
st.caption("RAG over ingested AWS documentation — retrieve, rerank, and generate answers")

mode = st.radio(
    "Mode",
    options=["Ask (RAG answer)", "Search only"],
    horizontal=True,
)

with st.sidebar:
    st.header("Settings")
    top_k = st.slider("Top K chunks for generation", min_value=1, max_value=10, value=5)
    service_filter = st.text_input("Filter by service (optional)", placeholder="Lambda")
    section_filter = st.text_input("Filter by section (optional)")
    st.info(
        "Ask mode: OpenSearch (top 20) → reranker (top 5) → Bedrock LLM.\n\n"
        "First startup may download ML models (~1.1GB reranker)."
    )

question = st.text_input(
    "Your question",
    placeholder="How should I use AWS Organizations with AWS Config?",
)

col1, col2, col3 = st.columns(3)
with col1:
    primary_clicked = st.button(
        "Get answer" if mode.startswith("Ask") else "Search",
        type="primary",
        use_container_width=True,
    )
with col2:
    health_clicked = st.button("Health (fast)", use_container_width=True)
with col3:
    ready_clicked = st.button("Ready check", use_container_width=True)


def _build_filters() -> dict | None:
    filters: dict = {}
    if service_filter.strip():
        filters["service"] = service_filter.strip()
    if section_filter.strip():
        filters["section"] = section_filter.strip()
    return filters or None


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
            st.error(f"Ready check timed out after {READY_TIMEOUT}s.")
        except httpx.HTTPError as exc:
            st.error(f"Backend unavailable: {exc}")

if primary_clicked:
    if not question.strip():
        st.warning("Please enter a question.")
    elif mode.startswith("Ask"):
        filters = _build_filters()
        with st.spinner("Retrieving documentation and generating answer..."):
            try:
                search_payload: dict = {"query": question.strip(), "top_k": top_k}
                if filters:
                    search_payload["filters"] = filters

                search_response = httpx.post(
                    f"{BACKEND_API_URL}/search",
                    json=search_payload,
                    timeout=SEARCH_TIMEOUT,
                )
                search_response.raise_for_status()
                search_data = search_response.json()
                chunks = search_data.get("results", [])

                if not chunks:
                    st.info(
                        "No matching documentation found. Try a different question or filters."
                    )
                else:
                    gen_response = httpx.post(
                        f"{BACKEND_API_URL}/generate",
                        json={"question": question.strip(), "chunks": chunks},
                        timeout=GENERATION_TIMEOUT,
                    )
                    gen_response.raise_for_status()
                    data = gen_response.json()

                    st.subheader("Answer")
                    st.markdown(data.get("answer", ""))

                    st.subheader("Sources")
                    sources = data.get("sources", [])
                    if not sources:
                        st.caption("No sources returned.")
                    else:
                        for source in sources:
                            page = source.get("page_number")
                            page_label = f"p. {page}" if page is not None else "page —"
                            section = source.get("section_title") or "—"
                            st.markdown(
                                f"- **{source.get('document_name', 'Document')}** · "
                                f"{section} · {page_label}"
                            )

                    st.caption(
                        f"Model: `{data.get('model_id', '—')}` · "
                        f"Latency: {data.get('latency_ms', 0):.0f} ms · "
                        f"Chunks used: {len(chunks)}"
                    )

            except httpx.TimeoutException:
                st.error(
                    "Request timed out. The reranker or Bedrock may still be warming up — retry shortly."
                )
            except httpx.ConnectError:
                st.error(
                    f"Cannot reach backend at `{BACKEND_API_URL}`. "
                    "Start the API: `cd backend/src && uv run uvicorn main:app --host 0.0.0.0 --port 8000`"
                )
            except httpx.HTTPStatusError as exc:
                st.error(f"Request failed ({exc.response.status_code}): {exc.response.text}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
    else:
        payload: dict = {"query": question.strip(), "top_k": top_k}
        filters = _build_filters()
        if filters:
            payload["filters"] = filters

        with st.spinner("Searching documentation..."):
            try:
                response = httpx.post(
                    f"{BACKEND_API_URL}/search",
                    json=payload,
                    timeout=SEARCH_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException:
                st.error(f"Search timed out after {SEARCH_TIMEOUT}s.")
            except httpx.ConnectError:
                st.error(f"Cannot reach backend at `{BACKEND_API_URL}`.")
            except httpx.HTTPStatusError as exc:
                st.error(f"Search failed ({exc.response.status_code}): {exc.response.text}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
            else:
                results = data.get("results", [])
                st.subheader(f"Results for: {data.get('query', question)}")
                st.write(f"Found **{len(results)}** result(s)")

                if not results:
                    st.info("No matching chunks found.")
                else:
                    for index, result in enumerate(results, start=1):
                        title = result.get("document_title") or result.get("title") or "Untitled"
                        section = result.get("section") or "—"
                        score = result.get("score", 0)
                        label = f"#{index} {result.get('service') or 'Doc'} · {title} (score: {score:.3f})"

                        with st.expander(label, expanded=index == 1):
                            st.markdown(f"**Section:** {section}")
                            if result.get("page_number") is not None:
                                st.markdown(f"**Page:** {result['page_number']}")
                            if result.get("source_url"):
                                st.markdown(f"**Source:** [{result['source_url']}]({result['source_url']})")
                            st.markdown("**Content**")
                            st.write(result.get("content", ""))

st.divider()
st.caption(f"Backend: `{BACKEND_API_URL}`")
