import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st

try:
    from src.agent import simple_agent
except ImportError:  # pragma: no cover - fallback for direct script execution
    from agent import simple_agent

st.set_page_config(page_title="Home RAG Assistant", layout="wide")

st.markdown(
    """
    <style>
    #MainMenu, footer, header {
        visibility: hidden;
    }

    .stApp {
        background: var(--background-color);
        color: var(--text-color);
    }

    section[data-testid="stSidebar"] {
        background: var(--secondary-background-color);
        border-right: 1px solid color-mix(in srgb, var(--text-color) 12%, transparent);
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }

    div.block-container {
        max-width: 1100px;
        padding-top: 1.25rem;
        padding-bottom: 5.5rem;
    }

    .hero-card {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-start;
        padding: 1.15rem 1.25rem;
        margin-bottom: 1rem;
        border-radius: 22px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        background: color-mix(in srgb, var(--secondary-background-color) 72%, transparent);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
    }

    .hero-title {
        margin: 0;
        font-size: 1.6rem;
        line-height: 1.15;
        font-weight: 650;
        letter-spacing: -0.03em;
    }

    .hero-subtitle {
        margin-top: 0.35rem;
        margin-bottom: 0;
        color: color-mix(in srgb, var(--text-color) 70%, transparent);
        font-size: 0.96rem;
        line-height: 1.5;
    }

    .hero-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        padding: 0.42rem 0.7rem;
        border-radius: 999px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        background: color-mix(in srgb, var(--background-color) 78%, transparent);
        font-size: 0.82rem;
        white-space: nowrap;
    }

    .hero-meta {
        display: flex;
        flex-wrap: wrap;
        gap: 0.5rem;
        justify-content: flex-end;
    }

    .composer-wrap {
        position: sticky;
        bottom: 0;
        z-index: 10;
        padding-top: 0.8rem;
        background: linear-gradient(
            180deg,
            color-mix(in srgb, var(--background-color) 0%, transparent),
            var(--background-color) 28%
        );
    }

    .composer-card {
        border-radius: 22px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        background: var(--background-color);
        box-shadow: 0 14px 30px rgba(0, 0, 0, 0.06);
        padding: 0.9rem 0.95rem 0.75rem;
    }

    section[data-testid="stSidebar"] [data-testid="stButton"] > button,
    .composer-card [data-testid="stButton"] > button,
    .composer-card button[kind="primaryFormSubmit"] {
        border-radius: 14px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
    }

    section[data-testid="stSidebar"] [data-testid="stButton"] > button {
        width: 100%;
        justify-content: flex-start;
    }

    .sidebar-section-title {
        margin: 1rem 0 0.5rem;
        font-size: 0.78rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: color-mix(in srgb, var(--text-color) 62%, transparent);
    }

    .sidebar-card {
        border-radius: 18px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        background: color-mix(in srgb, var(--background-color) 88%, transparent);
        padding: 0.8rem 0.85rem;
        margin-bottom: 0.6rem;
    }

    .sidebar-card-title {
        font-size: 0.92rem;
        font-weight: 650;
        margin-bottom: 0.25rem;
    }

    .sidebar-card-text {
        font-size: 0.84rem;
        line-height: 1.45;
        color: color-mix(in srgb, var(--text-color) 72%, transparent);
    }

    .history-card {
        border-radius: 16px;
        border: 1px solid color-mix(in srgb, var(--text-color) 10%, transparent);
        background: color-mix(in srgb, var(--background-color) 90%, transparent);
        padding: 0.75rem 0.8rem;
        margin-bottom: 0.55rem;
    }

    .history-role {
        font-size: 0.73rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: color-mix(in srgb, var(--text-color) 55%, transparent);
        margin-bottom: 0.25rem;
    }

    .history-preview {
        font-size: 0.84rem;
        line-height: 1.4;
        color: var(--text-color);
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
    }

    div[data-testid="stForm"] {
        border: 0;
        padding: 0;
        background: transparent;
    }

    div[data-testid="stTextInput"] input {
        border-radius: 14px;
        min-height: 3rem;
    }

    div[data-testid="stTextInput"] label {
        font-weight: 600;
    }

    .empty-state {
        border-radius: 22px;
        border: 1px dashed color-mix(in srgb, var(--text-color) 14%, transparent);
        background: color-mix(in srgb, var(--secondary-background-color) 64%, transparent);
        padding: 1.1rem 1.1rem 1rem;
        margin: 0.75rem 0 1rem;
    }

    .empty-state h3 {
        margin: 0 0 0.25rem;
        font-size: 1rem;
    }

    .empty-state p {
        margin: 0;
        color: color-mix(in srgb, var(--text-color) 72%, transparent);
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_answer" not in st.session_state:
    st.session_state.last_answer = ""

if "last_prompt" not in st.session_state:
    st.session_state.last_prompt = ""

if "submit_error" not in st.session_state:
    st.session_state.submit_error = ""


def format_preview(text: str, limit: int = 120) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + "…"


def get_conversation_turns() -> list[dict[str, str]]:
    turns = []
    pending_user = ""

    for message in st.session_state.messages:
        if message["role"] == "user":
            pending_user = message["content"]
            continue

        turns.append(
            {
                "user": pending_user,
                "assistant": message["content"],
            }
        )
        pending_user = ""

    return turns


def set_prompt(prompt_text: str) -> None:
    st.session_state.prompt_input = prompt_text
    st.session_state.submit_error = ""


def submit_prompt() -> None:
    user_input = st.session_state.prompt_input.strip()

    if not user_input:
        st.session_state.submit_error = "Please type a prompt first."
        return

    st.session_state.submit_error = ""
    st.session_state.last_prompt = user_input
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        try:
            answer = simple_agent(user_input)
        except Exception as exc:  # pragma: no cover - surfaced in UI
            answer = f"Error: {exc}"

    st.session_state.last_answer = answer
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.prompt_input = ""

with st.sidebar:
    st.markdown("## Home RAG Assistant")
    st.caption("Personal RAG workspace")

    st.markdown(
        """
        <div class="sidebar-card">
            <div class="sidebar-card-title">Workspace status</div>
            <div class="sidebar-card-text">Local-first retrieval with ChromaDB and OpenAI generation.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sidebar-section-title">Quick prompts</div>', unsafe_allow_html=True)
    if st.button("📋 Project summary"):
        set_prompt("Tóm tắt project cá nhân hiện tại của tôi.")
    if st.button("📚 Learning summary"):
        set_prompt("Tóm tắt các note học tập hiện tại của tôi.")
    if st.button("📅 Weekly plan"):
        set_prompt("Tạo weekly plan 7 ngày cho tôi.")
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.session_state.last_answer = ""
        st.session_state.last_prompt = ""
        st.session_state.prompt_input = ""
        st.session_state.submit_error = ""
        st.rerun()

    st.markdown('<div class="sidebar-section-title">Recent turns</div>', unsafe_allow_html=True)
    turns = get_conversation_turns()
    if not turns:
        st.markdown(
            """
            <div class="history-card">
                <div class="history-role">History</div>
                <div class="history-preview">No messages yet. Start with a prompt to build the thread here.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for index, turn in enumerate(reversed(turns[-6:]), start=1):
            user_preview = format_preview(turn["user"] or "No user prompt", 90)
            assistant_preview = format_preview(turn["assistant"], 120)
            st.markdown(
                f"""
                <div class="history-card">
                    <div class="history-role">Turn {index}</div>
                    <div class="history-preview"><strong>User:</strong> {user_preview}</div>
                    <div class="history-preview" style="margin-top: 0.35rem;"><strong>Assistant:</strong> {assistant_preview}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown(
    """
    <div class="hero-card">
        <div>
            <p class="hero-title">Home RAG Assistant</p>
            <p class="hero-subtitle">Claude-like layout for personal project notes, learning notes, and task summaries. The color palette still follows the current light/dark Streamlit theme.</p>
        </div>
        <div class="hero-meta">
            <div class="hero-badge">Local-first</div>
            <div class="hero-badge">ChromaDB</div>
            <div class="hero-badge">OpenAI</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if not st.session_state.messages:
    st.markdown(
        """
        <div class="empty-state">
            <h3>Start a conversation</h3>
            <p>Try asking for a project summary, learning note recap, or a weekly plan. The input box below accepts Enter to send and clears after submission.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

st.markdown('<div class="composer-wrap">', unsafe_allow_html=True)
st.markdown('<div class="composer-card">', unsafe_allow_html=True)
with st.form("prompt_form", clear_on_submit=False):
    input_col, button_col = st.columns([0.86, 0.14], vertical_alignment="bottom")
    with input_col:
        st.text_input(
            "Ask about your personal project, learning notes, or tasks...",
            key="prompt_input",
            label_visibility="collapsed",
            placeholder="Ask about your personal project, learning notes, or tasks...",
        )
    with button_col:
        st.form_submit_button("Send", use_container_width=True, on_click=submit_prompt)
st.markdown("</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.submit_error:
    st.warning(st.session_state.submit_error)
