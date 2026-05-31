"""AWS Documentation Assistant — conversational chat UI."""

import os
import uuid
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
CHAT_TIMEOUT = float(os.getenv("CHAT_TIMEOUT", "180"))
HEALTH_TIMEOUT = float(os.getenv("HEALTH_TIMEOUT", "10"))
READY_TIMEOUT = float(os.getenv("READY_TIMEOUT", "30"))
MAX_HISTORY_TURNS = int(os.getenv("MAX_HISTORY_TURNS", "10"))

st.set_page_config(
    page_title="AWS Docs Assistant",
    page_icon="☁️",
    layout="wide",
)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())


def _trim_history(messages: list[dict]) -> list[dict]:
    max_messages = MAX_HISTORY_TURNS * 2
    if len(messages) <= max_messages:
        return messages
    return messages[-max_messages:]


def _build_conversation_history(messages: list[dict]) -> list[dict]:
    history = []
    for message in messages:
        if message["role"] in {"user", "assistant"}:
            history.append({"role": message["role"], "content": message["content"]})
    return history


def _format_source(source: dict) -> str:
    document_name = source.get("document_name") or "Document"
    section_title = source.get("section_title")
    page_number = source.get("page_number")

    parts = [document_name]
    if section_title:
        parts.append(section_title)
    if page_number is not None:
        parts.append(f"Page {page_number}")
    return " | ".join(parts)


def _is_summary_request(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ("summarize", "summary", "recap", "our discussion"))


st.title("AWS Documentation Assistant")
st.caption("Conversational AWS specialist — intent-aware answers with source-grounded citations")

with st.sidebar:
    st.header("Status")
    if st.button("Health check", use_container_width=True):
        try:
            response = httpx.get(f"{BACKEND_API_URL}/health", timeout=HEALTH_TIMEOUT)
            response.raise_for_status()
            st.success(response.json())
        except httpx.HTTPError as exc:
            st.error(f"Backend unavailable: {exc}")

    if st.button("Ready check", use_container_width=True):
        try:
            response = httpx.get(f"{BACKEND_API_URL}/health/ready", timeout=READY_TIMEOUT)
            response.raise_for_status()
            body = response.json()
            if body.get("status") == "ok":
                st.success("Backend ready")
            else:
                st.warning(body)
        except httpx.HTTPError as exc:
            st.error(f"Ready check failed: {exc}")

    if st.button("Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.info(
        "The assistant detects intent (explain, compare, how-to, troubleshoot, summarize) "
        "and uses conversation memory for follow-ups without unnecessary retrieval."
    )

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        sources = message.get("sources") or []
        if sources:
            st.markdown("**Sources**")
            for source in sources:
                st.markdown(f"- {_format_source(source)}")
        if message.get("external_search_used"):
            st.caption("External AWS web search was used as fallback.")

prompt = st.chat_input("Ask an AWS question…")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.messages = _trim_history(st.session_state.messages)

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        spinner_text = (
            "Summarizing our conversation…"
            if _is_summary_request(prompt)
            else "Searching AWS documentation…"
        )
        with st.spinner(spinner_text):
            try:
                payload = {
                    "query": prompt.strip(),
                    "session_id": st.session_state.session_id,
                    "conversation_history": _build_conversation_history(
                        st.session_state.messages[:-1]
                    ),
                }
                response = httpx.post(
                    f"{BACKEND_API_URL}/chat",
                    json=payload,
                    timeout=CHAT_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.TimeoutException:
                st.error("Request timed out. Models may still be warming up — retry shortly.")
            except httpx.ConnectError:
                st.error(f"Cannot reach backend at `{BACKEND_API_URL}`.")
            except httpx.HTTPStatusError as exc:
                st.error(f"Request failed ({exc.response.status_code}): {exc.response.text}")
            except Exception as exc:
                st.error(f"Unexpected error: {exc}")
            else:
                answer = data.get("answer", "")
                sources = data.get("sources") or []
                external_used = bool(data.get("external_search_used"))

                st.markdown(answer)
                if sources:
                    st.markdown("**Sources**")
                    for source in sources:
                        st.markdown(f"- {_format_source(source)}")
                if external_used:
                    st.caption("External AWS web search was used as fallback.")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                        "external_search_used": external_used,
                    }
                )
                st.session_state.messages = _trim_history(st.session_state.messages)

st.divider()
st.caption(
    f"Backend: `{BACKEND_API_URL}` · Session: `{st.session_state.session_id[:8]}…` · "
    f"History limit: {MAX_HISTORY_TURNS} turns"
)
