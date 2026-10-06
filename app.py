"""Streamlit chat UI for the Medibank member support prototype. Run: streamlit run app.py"""

import streamlit as st

from src.agent import Agent
from src.models import ChatResponse
from src.retrieval import Retriever

DISCLAIMER = (
    "Prototype. Answers are general information from Medibank's Fund Rules and Member Guide, "
    "not advice about your specific cover. Check your Cover Summary or call 132 331."
)
EXAMPLES = [
    "What is the waiting period for pregnancy?",
    "Can I suspend my membership while I travel overseas?",
    "Is ambulance covered?",
    "Why was my last claim rejected?",
    "Should I get knee surgery or try physio first?",
]
DOC_LABELS = {"fund_rules": "Fund Rules", "member_guide": "Member Guide"}


@st.cache_resource(show_spinner="Loading documents and search index...")
def load_retriever() -> Retriever:
    """Loaded once per server and shared by every session."""
    return Retriever()


def render_response(response: ChatResponse, debug: bool) -> None:
    """Show one bot reply: the message, an escalation badge or citations, and the sources."""
    if response.escalation.escalate:
        st.warning(f"**Handed to a consultant** · {response.escalation.category.value.replace('_', ' ')}")
    st.markdown(response.message)

    if response.answer and response.answer.citations:
        cites = " · ".join(
            f"{DOC_LABELS[c.doc.value]} p.{c.page} ({c.section.split(' > ')[-1]})" for c in response.answer.citations
        )
        st.caption(f"Sources: {cites}")

    if response.sources and (debug or not response.escalation.escalate):
        with st.expander(f"Retrieved extracts ({len(response.sources)})"):
            for s in response.sources:
                c = s.chunk
                st.markdown(f"**{DOC_LABELS[c.doc.value]}, page {c.page}** · {c.section}")
                if debug:
                    st.caption(f"RRF {s.score:.4f} · semantic {s.semantic_score:.2f} · {c.chunk_id}")
                st.text(c.text[:600] + ("..." if len(c.text) > 600 else ""))

    if debug:
        e = response.escalation
        confidence = response.answer.confidence if response.answer else None
        st.caption(f"Debug · escalated={e.escalate} · category={e.category.value} · reason={e.reason or '-'} · confidence={confidence}")


st.set_page_config(page_title="Medibank Member Support", page_icon="💬")
st.title("Member Support Assistant")
st.caption(DISCLAIMER)

if "agent" not in st.session_state:
    st.session_state.agent = Agent(retriever=load_retriever())
    st.session_state.turns = []   # list of (question, ChatResponse)

with st.sidebar:
    st.header("Try a question")
    for example in EXAMPLES:
        if st.button(example, use_container_width=True):
            st.session_state.pending = example
    st.divider()
    debug = st.toggle("Show debug info")
    if st.button("New conversation"):
        st.session_state.agent = Agent(retriever=load_retriever())
        st.session_state.turns = []
        st.rerun()

for question, response in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        render_response(response, debug)

question = st.chat_input("Ask about your Medibank cover...") or st.session_state.pop("pending", None)
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Checking the Fund Rules and Member Guide..."):
            response = st.session_state.agent.handle(question)
        render_response(response, debug)
    st.session_state.turns.append((question, response))