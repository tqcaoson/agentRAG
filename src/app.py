import sys
from pathlib import Path

import streamlit as st


# =========================
# Path
# =========================

BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


# =========================
# Imports
# =========================

try:
    from src.agent import simple_agent
except ImportError:
    from agent import simple_agent


try:
    from src.ingest import DATA_DIR, ingest_file
except ImportError:
    from ingest import DATA_DIR, ingest_file


try:
    from src.tools import infer_generated_filename, is_file_generation_request
except ImportError:
    from tools import infer_generated_filename, is_file_generation_request



# =========================
# Streamlit config
# =========================

st.set_page_config(
    page_title="Home RAG Assistant",
    layout="wide"
)


# =========================
# CSS
# =========================

st.markdown(
    """
<style>

#MainMenu, footer, header {
    visibility:hidden;
}


.hero {
    padding:20px;
    border-radius:20px;
    border:1px solid rgba(120,120,120,.2);
    margin-bottom:20px;
}


.hero-title {
    font-size:28px;
    font-weight:700;
}


.hero-sub {
    opacity:.7;
}


.card {
    padding:15px;
    border-radius:16px;
    border:1px solid rgba(120,120,120,.2);
    margin-bottom:10px;
}


.history {
    padding:12px;
    border-radius:12px;
    border:1px solid rgba(120,120,120,.15);
    margin-bottom:8px;
    font-size:14px;
}


</style>
""",
    unsafe_allow_html=True,
)



# =========================
# Session State
# =========================

defaults = {
    "messages": [],
    "last_answer": "",
    "last_prompt": "",
    "submit_error": "",
    "composer_upload_nonce": 0,
    "generated_file_name": "assistant_answer.md",
    "generated_file_data": b"",
    "generated_file_mime": "application/octet-stream",
    "generated_file_is_image": False,
    "show_download": False,
}


for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value



# =========================
# Helpers
# =========================

def get_composer_upload_key():
    return (
        f"composer_files_"
        f"{st.session_state.composer_upload_nonce}"
    )


def set_prompt(text):

    st.session_state.prompt_input = text
    st.session_state.submit_error = ""



def format_preview(text, limit=120):

    text = " ".join(text.split())

    if len(text) <= limit:
        return text

    return text[:limit-1] + "..."



def get_turns():

    result = []

    user = ""

    for msg in st.session_state.messages:

        if msg["role"] == "user":
            user = msg["content"]

        elif msg["role"] == "assistant":

            result.append(
                {
                    "user": user,
                    "assistant": msg["content"]
                }
            )

            user = ""

    return result



def is_file_request(text):
    return is_file_generation_request(text)


def generated_file_mime(filename):
    extension = Path(filename).suffix.lower()
    return {
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".csv": "text/csv",
        ".json": "application/json",
        ".html": "text/html",
    }.get(extension, "application/octet-stream")



# =========================
# Submit
# =========================

def submit_prompt():

    user_input = st.session_state.prompt_input.strip()


    if not user_input:

        st.session_state.submit_error = (
            "Please type a prompt first."
        )

        return


    st.session_state.submit_error = ""

    st.session_state.last_prompt = user_input

    conversation_history = list(st.session_state.messages)

    st.session_state.messages.append(
        {
            "role":"user",
            "content":user_input
        }
    )


    # ingest attached files

    upload_key = get_composer_upload_key()

    uploaded = st.session_state.get(upload_key, [])


    if uploaded:

        upload_dir = DATA_DIR / "uploads"

        upload_dir.mkdir(
            parents=True,
            exist_ok=True
        )


        for file in uploaded:

            try:

                dest = upload_dir / file.name

                dest.write_bytes(
                    file.getvalue()
                )

                ingest_file(dest)


                st.session_state.messages.append(
                    {
                        "role":"system",
                        "content":
                        f"Ingested file: {file.name}"
                    }
                )


            except Exception as exc:

                st.session_state.messages.append(
                    {
                        "role":"system",
                        "content":
                        f"Error ingesting {file.name}: {exc}"
                    }
                )


    st.session_state.composer_upload_nonce += 1



    # agent

    with st.spinner("Thinking..."):

        try:

            answer = simple_agent(
                user_input,
                conversation_history=conversation_history,
            )


        except Exception as exc:

            answer = f"Error: {exc}"



    if hasattr(answer, "data") and hasattr(answer, "filename"):
        artifact = answer
        answer = artifact.preview
        st.session_state.generated_file_name = artifact.filename
        st.session_state.generated_file_data = artifact.data
        st.session_state.generated_file_mime = artifact.mime_type
        st.session_state.generated_file_is_image = artifact.mime_type.startswith("image/")
        st.session_state.show_download = True
    else:
        st.session_state.generated_file_name = infer_generated_filename(user_input)
        st.session_state.generated_file_data = answer
        st.session_state.generated_file_mime = generated_file_mime(st.session_state.generated_file_name)
        st.session_state.generated_file_is_image = False
        st.session_state.show_download = is_file_request(user_input) and not answer.startswith("Error:")

    st.session_state.last_answer = answer


    st.session_state.messages.append(
        {
            "role":"assistant",
            "content":answer
        }
    )


    st.session_state.prompt_input = ""
# =========================
# Sidebar
# =========================

with st.sidebar:

    st.markdown(
        """
        <div class="card">
            <h3>Home RAG Assistant</h3>
            <p>
            Personal knowledge assistant
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


    st.markdown(
        "### Quick prompts"
    )


    if st.button(
        "📋 Project summary",
        use_container_width=True
    ):

        set_prompt(
            "Tóm tắt project cá nhân hiện tại của tôi."
        )


    if st.button(
        "📚 Learning summary",
        use_container_width=True
    ):

        set_prompt(
            "Tóm tắt các note học tập hiện tại của tôi."
        )


    if st.button(
        "📅 Weekly plan",
        use_container_width=True
    ):

        set_prompt(
            "Tạo weekly plan 7 ngày cho tôi."
        )


    if st.button(
        "🗑 Clear chat",
        use_container_width=True
    ):

        st.session_state.messages = []
        st.session_state.last_answer = ""
        st.session_state.last_prompt = ""
        st.session_state.generated_file_data = b""
        st.session_state.generated_file_mime = "application/octet-stream"
        st.session_state.generated_file_is_image = False
        st.session_state.show_download = False

        st.rerun()



    # =====================
    # History
    # =====================

    st.markdown(
        "### Recent turns"
    )


    turns = get_turns()


    if not turns:

        st.caption(
            "No conversation yet."
        )


    else:

        for i, turn in enumerate(
            reversed(turns[-5:]),
            start=1
        ):

            st.markdown(
                f"""
                <div class="history">

                <b>Turn {i}</b>

                <br><br>

                <b>User:</b>
                {format_preview(turn["user"],80)}

                <br>

                <b>Assistant:</b>
                {format_preview(turn["assistant"],100)}

                </div>
                """,
                unsafe_allow_html=True
            )



    # =====================
    # Upload Knowledge
    # =====================

    st.markdown(
        "### Add documents"
    )


    with st.expander(
        "Upload files"
    ):

        files = st.file_uploader(
            "Select files",
            accept_multiple_files=True
        )


        if st.button(
            "Upload & Ingest"
        ):


            if not files:

                st.warning(
                    "No files selected"
                )


            else:

                upload_dir = DATA_DIR / "uploads"

                upload_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )


                for file in files:

                    try:

                        dest = (
                            upload_dir /
                            file.name
                        )

                        dest.write_bytes(
                            file.getvalue()
                        )


                        ingest_file(
                            dest
                        )


                        st.success(
                            f"Ingested {file.name}"
                        )


                    except Exception as exc:

                        st.error(
                            str(exc)
                        )



    # =====================
    # Create knowledge file
    # =====================

    with st.expander(
        "Create knowledge file"
    ):


        try:

            folders = [
                p.name
                for p in DATA_DIR.iterdir()
                if p.is_dir()
            ]

        except Exception:

            folders = []


        folder = st.selectbox(
            "Folder",
            folders or ["uploads"]
        )


        filename = st.text_input(
            "Filename",
            placeholder="note.md"
        )


        content = st.text_area(
            "Content",
            height=150
        )



        if st.button(
            "Create & Ingest"
        ):


            if not filename or not content:

                st.warning(
                    "Missing filename/content"
                )


            else:

                target_dir = (
                    DATA_DIR /
                    folder
                )


                target_dir.mkdir(
                    parents=True,
                    exist_ok=True
                )


                dest = (
                    target_dir /
                    filename
                )


                dest.write_text(
                    content,
                    encoding="utf-8"
                )


                try:

                    ingest_file(
                        dest
                    )

                    st.success(
                        f"Created {dest}"
                    )


                except Exception as exc:

                    st.error(
                        str(exc)
                    )



# =========================
# Main UI
# =========================


st.markdown(
    """
    <div class="hero">

    <div class="hero-title">
    Home RAG Assistant
    </div>

    <div class="hero-sub">
    Personal project notes, learning notes,
    tasks and document search.
    </div>

    </div>
    """,
    unsafe_allow_html=True
)



if not st.session_state.messages:

    st.info(
        "Start conversation with your notes."
    )



# Chat messages

for msg in st.session_state.messages:


    with st.chat_message(
        msg["role"]
    ):

        st.markdown(
            msg["content"]
        )



# =========================
# Composer
# =========================

with st.form(
    "prompt_form",
    clear_on_submit=False
):


    st.text_input(
        "Prompt",
        key="prompt_input",
        placeholder=
        "Ask about your project, notes..."
    )


    st.file_uploader(
        "Attach files",
        key=get_composer_upload_key(),
        accept_multiple_files=True
    )


    st.form_submit_button(
        "Send",
        use_container_width=True,
        on_click=submit_prompt
    )



# =========================
# Download generated file
# =========================


if (
    st.session_state.last_answer
    and
    st.session_state.show_download
):


    if st.session_state.generated_file_is_image:
        st.image(st.session_state.generated_file_data, caption=st.session_state.generated_file_name)

    st.download_button(

        label=
        f"Download {st.session_state.generated_file_name}",

        data=
        st.session_state.generated_file_data,

        file_name=
        st.session_state.generated_file_name,

        mime=st.session_state.generated_file_mime,

        use_container_width=True
    )



if st.session_state.submit_error:

    st.warning(
        st.session_state.submit_error
    )
