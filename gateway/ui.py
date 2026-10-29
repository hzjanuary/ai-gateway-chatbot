"""Optional Streamlit views. No server-side inference token is supplied to browsers."""

import os
import secrets

import httpx

from gateway.config import ConfigError, load_settings, token_hash


def main(role: str | None = None) -> None:
    import streamlit as st

    role = role or os.environ.get("GATEWAY_UI_ROLE", "chat")
    st.set_page_config(page_title=f"AI Gateway Multi-Node · {role}")
    st.title(
        "AI Gateway Multi-Node · Administration" if role == "admin" else "AI Gateway Multi-Node"
    )
    expected = None
    if role == "admin":
        try:
            expected = load_settings().admin_hash
        except ConfigError:
            st.error("Admin UI disabled: invalid private configuration.")
            st.stop()
        if not expected:
            st.error("Admin UI disabled: no admin secret configured.")
            st.stop()
    token = st.text_input("Admin token" if role == "admin" else "Inference token", type="password")
    if not token or (expected and not secrets.compare_digest(token_hash(token), expected)):
        st.info("A valid role token is required.")
        st.stop()
    url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
    try:
        with httpx.Client(trust_env=False, timeout=65, follow_redirects=False) as client:
            headers = {"Authorization": f"Bearer {token}"}
            if role == "admin":
                response = client.get(url + "/v1/monitoring/stats", headers=headers)
                if response.status_code != 200:
                    st.error("Backend denied administration.")
                    st.stop()
                st.json(response.json())
                logs = client.get(url + "/v1/monitoring/logs", headers=headers)
                if logs.status_code == 200:
                    st.json(logs.json())
                strategy = st.selectbox(
                    "Selection strategy", ["round_robin", "least_used", "random"]
                )
                if st.button("Apply strategy"):
                    changed = client.post(
                        url + f"/v1/providers/strategy/{strategy}", headers=headers
                    )
                    st.write("Updated" if changed.status_code == 200 else "Denied")
                confirmed = st.checkbox("Confirm circuit reset; quota reservations remain spent")
                if st.button("Reset circuits", disabled=not confirmed):
                    changed = client.post(
                        url + "/v1/providers/reset", headers=headers, json={"confirm": confirmed}
                    )
                    st.write(
                        "Reset" if changed.status_code == 200 else "Denied or requests still active"
                    )
            else:
                response = client.get(url + "/v1/models", headers=headers)
                if response.status_code != 200:
                    st.error("Backend denied inference access.")
                    st.stop()
                choices = response.json()["models"]
                if not choices:
                    st.warning("No authorized providers. Ask the local operator to register one.")
                    st.stop()
                provider = st.selectbox("Provider", [item["provider"] for item in choices])
                enrichment = st.checkbox(
                    "Web enrichment (sends a bounded query externally)", value=False
                )
                prompt = st.chat_input("Message")
                if prompt:
                    result = client.post(
                        url + "/v1/inference",
                        headers=headers,
                        json={
                            "prompt": prompt,
                            "provider": provider,
                            "web_enrichment": enrichment,
                            "stream": False,
                        },
                    )
                    if result.status_code != 200:
                        st.error(f"Inference failed (HTTP {result.status_code}).")
                    else:
                        data = result.json()
                        st.write(data["response"])
                        st.caption(f"{data['provider']} · {data['model']}")
                        for source in data["sources"]:
                            # Plain text URLs; no provider HTML or unsafe markdown interpolation.
                            st.write(source["url"])
    except httpx.HTTPError:
        st.error("Gateway connection failed.")


if __name__ == "__main__":
    main()
