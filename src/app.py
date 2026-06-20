import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import settings, logger
from src.classifier import classify_persona, detect_escalation_triggers
from src.rag_pipeline import RAGPipeline
from src.generator import ResponseGenerator
from src.escalator import EscalationEngine, AnalyticsCounter


@st.cache_resource
def init_rag():
    return RAGPipeline()


@st.cache_resource
def init_generator():
    return ResponseGenerator()


@st.cache_resource
def init_escalator():
    return EscalationEngine()


@st.cache_resource
def init_analytics():
    return AnalyticsCounter()


@st.cache_resource
def load_kb(_rag):
    count = _rag.load_knowledge_base()
    return count


def main():
    st.set_page_config(
        page_title="AdSparkX Persona-Adaptive Support",
        page_icon="🤖",
        layout="wide",
    )

    # -- Header ------------------------------------------------------------
    st.title("🤖 AdSparkX Persona-Adaptive Customer Support")
    st.markdown(
        "This system detects your **persona**, retrieves relevant documentation, "
        "and tailors responses accordingly. If needed, it can **escalate** to a human agent."
    )

    # -- Validate API Key --------------------------------------------------
    if not settings.GEMINI_API_KEY:
        st.error(
            "⚠️  GEMINI_API_KEY is not set. "
            "Create a `.env` file in the project root with `GEMINI_API_KEY=your_key_here` "
            "and restart the app."
        )
        st.stop()

    # -- Initialize components ---------------------------------------------
    rag = init_rag()
    generator = init_generator()
    escalator = init_escalator()
    analytics = init_analytics()

    kb_count = load_kb(rag)
    if kb_count == 0:
        st.warning(
            "⚠️  No documents found in the knowledge base. "
            "Add support documents to the `knowledge_base/` folder and restart."
        )

    # -- Sidebar -----------------------------------------------------------
    with st.sidebar:
        st.header("📊 Session Stats")
        summary = analytics.get_summary()
        col1, col2 = st.columns(2)
        col1.metric("Total Queries", summary["total_queries"])
        col2.metric("Escalations", summary["escalations"])

        st.subheader("Persona Distribution")
        for persona, count in summary["persona_counts"].items():
            st.text(f"{persona}: {count}")

        st.divider()
        st.subheader("🔧 KB Status")
        st.text(f"Chunks Loaded: {kb_count}")

        if st.button("🔄 Reload Knowledge Base", type="secondary"):
            load_kb.clear()
            load_kb(rag)
            st.rerun()

        st.divider()
        st.caption("Powered by Google Gemini + ChromaDB")

        st.divider()
        show_debug = st.checkbox("🔍 Show Debug Info", value=False, help="Display raw persona scores, sentiment, and token usage")

    # -- Initialize session state ------------------------------------------
    if "history" not in st.session_state:
        st.session_state.history = []
    if "show_debug" not in st.session_state:
        st.session_state.show_debug = False

    # -- Main chat interface -----------------------------------------------
    for turn in st.session_state.history:
        with st.chat_message("user"):
            st.markdown(turn["query"])
        with st.chat_message("assistant"):
            _render_response(turn, show_debug)

    query = st.chat_input("Type your support query here...")

    if not query:
        return

    # -- Show user query ---------------------------------------------------
    with st.chat_message("user"):
        st.markdown(query)

    # -- 1. Classify Persona -----------------------------------------------
    with st.status("🔍 Analyzing...", expanded=True) as status:
        st.write("**Step 1:** Detecting persona...")
        persona, persona_confidence, persona_details = classify_persona(
            query, st.session_state.history
        )
        st.write(f"→ Persona: **{persona}** (confidence: {persona_confidence:.2%})")

        # -- 2. RAG Retrieval ----------------------------------------------
        st.write("**Step 2:** Retrieving relevant documents...")
        retrieval_result = rag.query(query)
        retrieved_chunks = retrieval_result["results"]
        retrieval_conf = rag.retrieval_confidence(retrieved_chunks)
        st.write(
            f"→ Retrieved {len(retrieved_chunks)} chunks "
            f"(max confidence: {retrieval_conf:.2%})"
        )

        escalation_triggers = detect_escalation_triggers(query)

        # -- 3. Generate Response ------------------------------------------
        st.write("**Step 3:** Generating persona-adaptive response...")
        generation_result = generator.generate(
            persona=persona,
            query=query,
            retrieved_chunks=retrieved_chunks,
            conversation_history=st.session_state.history,
        )
        response_text = generation_result["response"]
        st.write("✅ Response generated.")

        # -- 4. Escalation Check -------------------------------------------
        st.write("**Step 4:** Evaluating escalation...")
        escalation_result = escalator.evaluate(
            query=query,
            persona=persona,
            persona_confidence=persona_confidence,
            retrieval_results=retrieved_chunks,
            escalation_triggers=escalation_triggers,
            conversation_history=st.session_state.history,
        )
        if escalation_result["should_escalate"]:
            st.write(
                f"⚠️ Escalation recommended (priority: **{escalation_result['priority']}**)"
            )
        else:
            st.write("✅ No escalation needed.")

        status.update(label="✅ Analysis complete", state="complete")

    # -- 5. Handoff Summary (if escalated) ---------------------------------
    handoff = None
    if escalation_result["should_escalate"]:
        handoff = escalator.generate_handoff(
            query=query,
            response=response_text,
            persona=persona,
            persona_confidence=persona_confidence,
            retrieval_results=retrieved_chunks,
            escalation_result=escalation_result,
            conversation_history=st.session_state.history,
        )

    # -- 6. Build turn data ------------------------------------------------
    turn_data = {
        "query": query,
        "persona": persona,
        "persona_confidence": persona_confidence,
        "persona_details": persona_details,
        "retrieved_chunks": retrieved_chunks,
        "response": response_text,
        "generation_info": generation_result,
        "escalation": escalation_result,
        "handoff": handoff,
        "escalation_triggers": escalation_triggers,
    }

    # -- Track analytics ---------------------------------------------------
    analytics.track_query(persona, escalation_result["should_escalate"])

    # -- Append to history -------------------------------------------------
    st.session_state.history.append(turn_data)

    # -- Render assistant response -----------------------------------------
    with st.chat_message("assistant"):
        _render_response(turn_data, show_debug)

    # -- Force rerun to update sidebar stats -------------------------------
    st.rerun()


def _render_response(turn: Dict[str, Any], show_debug: bool = False):
    st.markdown(turn["response"])

    # Confidence & Persona row
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"**🧑 Persona:** {turn['persona']} "
            f"({turn['persona_confidence']:.1%})"
        )
    with col2:
        sentiment = turn.get("persona_details", {}).get("sentiment", {})
        label = sentiment.get("label", "unknown").capitalize()
        score = sentiment.get("score", 0)
        st.markdown(f"**💬 Sentiment:** {label} ({score:.1%})")
    with col3:
        st.markdown(f"**📊 Retrieval Confidence:** {_max_retrieval_conf(turn):.1%}")

    # Sources
    chunks = turn.get("retrieved_chunks", [])
    if chunks:
        with st.expander("📄 Retrieved Sources", expanded=False):
            for i, chunk in enumerate(chunks):
                st.markdown(
                    f"**Source {i+1}:** `{chunk['source']}` "
                    f"(confidence: {chunk['confidence']:.1%})"
                )
                st.text(chunk["content"][:300] + ("..." if len(chunk["content"]) > 300 else ""))

    # Escalation status
    esc = turn.get("escalation", {})
    if esc.get("should_escalate"):
        st.warning(
            f"⚠️ **Escalation Recommended** — "
            f"Priority: **{esc['priority'].upper()}**"
        )
        for reason in esc.get("reasons", []):
            st.markdown(f"- {reason['detail']}")

    # Handoff summary
    handoff = turn.get("handoff")
    if handoff:
        with st.expander("🚨 Human Handoff Summary", expanded=True):
            st.json(handoff)

    # Debug metadata
    if show_debug:
        with st.expander("🔍 Debug Info", expanded=False):
            meta = {
                "persona_raw_scores": turn.get("persona_details", {}).get("raw_scores", {}),
                "sentiment": turn.get("persona_details", {}).get("sentiment", {}),
                "generation": {
                    "finish_reason": turn.get("generation_info", {}).get("finish_reason", "N/A"),
                    "token_usage": turn.get("generation_info", {}).get("token_usage", {}),
                },
                "escalation_triggers": turn.get("escalation_triggers", []),
            }
            st.json(meta)


def _max_retrieval_conf(turn: Dict[str, Any]) -> float:
    chunks = turn.get("retrieved_chunks", [])
    if not chunks:
        return 0.0
    return max(c["confidence"] for c in chunks)


if __name__ == "__main__":
    main()
