"""Minimal Streamlit app for EC2 smoke tests."""

import os
from pathlib import Path

import httpx
import streamlit as st
from dotenv import load_dotenv

_FRONTEND_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_FRONTEND_ROOT / ".env")

API_BASE = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")

st.set_page_config(page_title="Hello World", page_icon="👋")
st.title("Hello World from Streamlit")
st.write("If you see this, Streamlit is running on EC2.")

st.caption(f"Backend URL: `{API_BASE}`")

if st.button("Ping backend /health"):
    try:
        response = httpx.get(f"{API_BASE}/health", timeout=5.0)
        response.raise_for_status()
        st.success(response.json())
    except Exception as exc:
        st.error(f"Backend unreachable: {exc}")
