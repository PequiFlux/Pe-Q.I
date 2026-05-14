from __future__ import annotations

from pathlib import Path

import streamlit as st

STYLE_PATHS = [
    Path(__file__).with_name("styles.base.css"),
    Path(__file__).with_name("styles.surface.css"),
    Path(__file__).with_name("styles.demo.css"),
]


def inject_styles() -> None:
    stylesheet = "\n".join(path.read_text(encoding="utf-8") for path in STYLE_PATHS)
    st.markdown(f"<style>{stylesheet}</style>", unsafe_allow_html=True)
