from __future__ import annotations

import json


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="PequiFlux Yard Copilot", layout="wide")
    st.title("PequiFlux Yard Copilot")
    st.caption("Modular-monolith UI shell. The decision engine must be wired with a Gemma runtime.")
    st.info(
        "This UI is intentionally thin. It should render a single FrontEndPayload without additional safety logic."
    )
    st.code(
        json.dumps(
            {
                "expected_payload": "FrontEndPayload",
                "modules": [
                    "orchestration",
                    "domain",
                    "audit",
                    "storage",
                    "gemma",
                ],
            },
            indent=2,
        ),
        language="json",
    )


if __name__ == "__main__":
    main()

