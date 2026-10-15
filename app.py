"""Provided customer demo client; all assessment facts come from participant API."""

import os
from pathlib import Path

import httpx
import streamlit as st

from ui_contract import fetch_assessment, load_personas, select_persona, send_message


BASE_URL = os.getenv("BANK_API_URL", "http://127.0.0.1:8000")
CATALOG = Path(os.getenv("DEMO_PERSONAS_PATH", "demo_personas.json"))
st.set_page_config(page_title="Your classroom credit assessment", page_icon="🏦")
st.title("Your classroom credit assessment")
st.caption("Fictional customer data and policy for learning. No real credit decision is made.")

try:
    personas = load_personas(CATALOG)
except (OSError, ValueError):
    st.error("Demo personas are unavailable. Check DEMO_PERSONAS_PATH.")
    st.stop()

selected = st.selectbox("Demo customer", personas, format_func=lambda item: item["label"])
select_persona(st.session_state, selected)
st.info(selected["scenario"])
st.caption(f"Fictional customer: {selected['customer_id']}")
token = selected["demo_token"]

with httpx.Client(timeout=20) as client:
    status, facts = fetch_assessment(client, BASE_URL, token)
if status == "available" and facts is not None:
    left, middle, right = st.columns(3)
    left.metric("Classroom score", f"{facts['score']} / 850")
    middle.metric("36-month average", f"IDR {facts['average_balance_36m']:,.0f}")
    right.metric("Classroom card limit", f"IDR {facts['credit_limit_idr']:,}")
    st.caption(f"Assessment date: {facts['as_of_date']} · Model: {facts['model_version']}")
    if facts.get("explanation_status") == "available":
        with st.expander("Model-path evidence"):
            for reason in facts["reason_codes"]:
                st.write(f"• {reason['description']}")
    else:
        st.warning("Verified reason evidence is unavailable. Ask for a record review.")
elif status == "unavailable":
    st.warning("This customer's assessment is unavailable. Ask the agent for an explanation.")
else:
    st.error("The participant API is unavailable or returned an invalid response.")

st.subheader("Ask about this assessment")
for turn in st.session_state.conversation:
    with st.chat_message(turn["role"]):
        st.write(turn["content"])
question = st.chat_input("Why did I receive this score?")
if question:
    with httpx.Client(timeout=25) as client:
        reply, outcome = send_message(client, BASE_URL, token, question,
                                      st.session_state.conversation)
    st.session_state.conversation.extend([
        {"role": "user", "content": question[:1000]},
        {"role": "assistant", "content": reply[:1000]},
    ])
    st.rerun()
