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


try:
    from src import knowledge
except ImportError:
    import knowledge



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
    "page": "💬 Chat",
    "editing_source": None,
    "delete_confirm_source": None,
    "confirm_reingest_all": False,
    "confirm_wipe_vectors": False,
    "knowledge_notice": None,
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


def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"


def set_knowledge_notice(kind, text):
    """Lưu thông báo để hiện 1 lần sau khi rerun (flash message)."""
    st.session_state.knowledge_notice = (kind, text)


def show_knowledge_notice():
    notice = st.session_state.knowledge_notice
    st.session_state.knowledge_notice = None
    if not notice:
        return
    kind, text = notice
    if kind == "success":
        st.success(text)
    elif kind == "warning":
        st.warning(text)
    else:
        st.error(text)



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

def render_sidebar():
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

        st.radio(
            "Trang",
            ["💬 Chat", "📚 Quản lý Knowledge"],
            key="page",
            label_visibility="collapsed",
        )

        if st.session_state.page == "💬 Chat":
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
# Chat page
# =========================

def render_chat_page():
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



# =========================
# Knowledge management page
# =========================

STATUS_LABEL = {
    "indexed": "✅ Đã train",
    "not_indexed": "⏳ Chưa train",
    "unknown": "❓ Không rõ (mất kết nối Qdrant)",
}


def render_knowledge_page():
    st.markdown(
        """
        <div class="hero">

        <div class="hero-title">
        📚 Quản lý Knowledge
        </div>

        <div class="hero-sub">
        Xem, sửa, xóa tài liệu đã train. Mọi thay đổi đều đồng bộ
        cả file gốc và vector trong Qdrant.
        </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    show_knowledge_notice()

    # ---------- Tổng quan ----------
    try:
        stats = knowledge.get_stats()
    except Exception as exc:
        st.error(f"Không lấy được trạng thái knowledge: {exc}")
        stats = None

    if stats is not None:
        if stats["qdrant_ok"]:
            st.success(
                f"Qdrant đang chạy — collection `{stats['collection']}`"
                + (f", vector {stats['vector_size']} chiều"
                   if stats["vector_size"] else ", chưa có collection")
                + f" — embedding `{stats['embedding_model']}`."
            )
        else:
            st.error(
                "Không kết nối được Qdrant. Vẫn xem/sửa/xóa được file, "
                "nhưng train lại cần Qdrant đang chạy. "
                f"Chi tiết: {stats['qdrant_message']}"
            )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Tài liệu trên đĩa", stats["docs_on_disk"])
        col2.metric("Tài liệu đã train", stats["docs_indexed"])
        col3.metric("Tổng vector (chunk)", stats["points_count"])
        col4.metric(
            "Vector rác",
            stats["orphan_chunks"],
            help="Chunk của file đã bị xóa khỏi đĩa nhưng vector còn trong Qdrant.",
        )

    # ---------- Tác vụ chung ----------
    st.markdown("### Tác vụ chung")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "🔄 Train lại toàn bộ",
            use_container_width=True,
            help="Xóa sạch vector rồi train lại mọi file trong data/knowledge.",
        ):
            st.session_state.confirm_reingest_all = True
    with col2:
        if st.button(
            "🧹 Dọn vector rác",
            use_container_width=True,
            disabled=not stats or stats["orphan_chunks"] == 0,
            help="Xóa vector của các file đã bị xóa khỏi đĩa.",
        ):
            with st.spinner("Đang dọn vector rác..."):
                try:
                    result = knowledge.delete_orphans()
                    set_knowledge_notice(
                        "success",
                        f"Đã dọn {result['deleted_chunks']} vector rác "
                        f"của {result['sources']} file.",
                    )
                except Exception as exc:
                    set_knowledge_notice("error", f"Dọn vector rác thất bại: {exc}")
            st.rerun()

    if st.session_state.confirm_reingest_all:
        st.warning(
            "Train lại toàn bộ sẽ xóa sạch vector cũ rồi embed lại mọi file. "
            "Việc này tốn phí embedding OpenAI theo dung lượng knowledge."
        )
        col_yes, col_no = st.columns(2)
        with col_yes:
            if st.button("✅ Xác nhận train lại", use_container_width=True):
                st.session_state.confirm_reingest_all = False
                with st.spinner("Đang train lại toàn bộ knowledge..."):
                    try:
                        result = knowledge.reingest_all()
                        set_knowledge_notice(
                            "success",
                            f"Đã train lại {result['chunks']} chunk.",
                        )
                    except Exception as exc:
                        set_knowledge_notice("error", f"Train lại thất bại: {exc}")
                st.rerun()
        with col_no:
            if st.button("Hủy", use_container_width=True):
                st.session_state.confirm_reingest_all = False
                st.rerun()

    # ---------- Danh sách tài liệu ----------
    st.markdown("### Tài liệu")

    try:
        documents = knowledge.list_documents()
    except Exception as exc:
        st.error(f"Không liệt kê được tài liệu: {exc}")
        documents = []

    if not documents:
        st.info(
            "Chưa có tài liệu nào trong `data/knowledge/`. "
            "Thêm file bằng mục Upload ở sidebar, hoặc copy file .md/.txt/.csv "
            "vào thư mục `data/knowledge/` rồi bấm Train lại toàn bộ."
        )
        return

    folders = sorted({doc["folder"] for doc in documents})
    filter_col1, filter_col2 = st.columns([2, 1])
    with filter_col1:
        keyword = st.text_input(
            "🔎 Lọc theo tên file",
            placeholder="vd: rag, requirements...",
        ).strip().lower()
    with filter_col2:
        folder_filter = st.selectbox(
            "Thư mục",
            ["Tất cả"] + folders,
        )

    visible = [
        doc for doc in documents
        if (not keyword or keyword in doc["name"].lower())
        and (folder_filter == "Tất cả" or doc["folder"] == folder_filter)
    ]

    if not visible:
        st.info("Không có tài liệu nào khớp bộ lọc.")
        return

    for index, doc in enumerate(visible):
        source = doc["source"]
        chunks_label = (
            f"{doc['chunks']} chunk" if doc["chunks"] is not None else "? chunk"
        )
        header = (
            f"📄 {source} — {chunks_label} · "
            f"{format_size(doc['size_bytes'])} · {doc['modified']} · "
            f"{STATUS_LABEL.get(doc['status'], doc['status'])}"
        )
        with st.expander(header):
            # ----- Chế độ sửa -----
            if st.session_state.editing_source == source:
                try:
                    original = knowledge.read_document(source)
                except Exception as exc:
                    st.error(str(exc))
                    original = ""
                edited = st.text_area(
                    "Nội dung",
                    value=original,
                    height=300,
                    key=f"edit_area_{index}",
                )
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("💾 Lưu & train lại", key=f"save_{index}"):
                        with st.spinner("Đang lưu và train lại..."):
                            try:
                                result = knowledge.save_document(source, edited)
                                st.session_state.editing_source = None
                                set_knowledge_notice(
                                    "success",
                                    f"Đã lưu {source} và train lại "
                                    f"{result['chunks']} chunk.",
                                )
                            except Exception as exc:
                                set_knowledge_notice("error", f"Lưu thất bại: {exc}")
                        st.rerun()
                with btn_col2:
                    if st.button("Hủy sửa", key=f"cancel_edit_{index}"):
                        st.session_state.editing_source = None
                        st.rerun()
                continue

            # ----- Chế độ xem + tác vụ -----
            st.caption(
                f"Thư mục: `{doc['folder']}` · "
                f"Sửa lần cuối: {doc['modified']}"
            )
            action_col1, action_col2, action_col3 = st.columns(3)
            with action_col1:
                if st.button("✏️ Sửa", key=f"edit_{index}", use_container_width=True):
                    st.session_state.editing_source = source
                    st.session_state.delete_confirm_source = None
                    st.rerun()
            with action_col2:
                if st.button(
                    "🔄 Train lại",
                    key=f"reingest_{index}",
                    use_container_width=True,
                    help="Embed lại file này (dùng khi đã sửa file ngoài UI).",
                ):
                    with st.spinner("Đang train lại file..."):
                        try:
                            result = knowledge.reingest_document(source)
                            set_knowledge_notice(
                                "success",
                                f"Đã train lại {source}: "
                                f"{result['chunks']} chunk.",
                            )
                        except Exception as exc:
                            set_knowledge_notice("error", f"Train lại thất bại: {exc}")
                    st.rerun()
            with action_col3:
                if st.button("🗑 Xóa", key=f"delete_{index}", use_container_width=True):
                    st.session_state.delete_confirm_source = source
                    st.session_state.editing_source = None
                    st.rerun()

            # ----- Xác nhận xóa -----
            if st.session_state.delete_confirm_source == source:
                st.warning(
                    f"Xóa **{source}**? File gốc sẽ bị xóa khỏi đĩa và "
                    "toàn bộ vector của nó sẽ bị xóa khỏi Qdrant. "
                    "Không khôi phục được."
                )
                confirm_col1, confirm_col2 = st.columns(2)
                with confirm_col1:
                    if st.button(
                        "✅ Xác nhận xóa",
                        key=f"confirm_delete_{index}",
                        use_container_width=True,
                    ):
                        try:
                            result = knowledge.delete_document(source)
                            st.session_state.delete_confirm_source = None
                            set_knowledge_notice(
                                "success",
                                f"Đã xóa {source} và "
                                f"{result['deleted_chunks']} vector.",
                            )
                        except Exception as exc:
                            set_knowledge_notice("error", f"Xóa thất bại: {exc}")
                        st.rerun()
                with confirm_col2:
                    if st.button(
                        "Hủy",
                        key=f"cancel_delete_{index}",
                        use_container_width=True,
                    ):
                        st.session_state.delete_confirm_source = None
                        st.rerun()

            # ----- Xem chunk đã train -----
            # Streamlit cấm expander lồng trong expander, nên dùng
            # checkbox để hiện/ẩn danh sách chunk ngay trong expander
            # của tài liệu thay vì mở thêm 1 expander con.
            if doc["chunks"]:
                show_chunks = st.checkbox(
                    f"Xem {doc['chunks']} chunk đã train",
                    key=f"showchunks_{index}",
                )
                if show_chunks:
                    try:
                        chunks = knowledge.list_chunks(source)
                    except Exception as exc:
                        st.error(f"Không tải được chunk: {exc}")
                        chunks = []
                    for chunk in chunks:
                        preview = format_preview(chunk["content"], 300)
                        chunk_col1, chunk_col2 = st.columns([5, 1])
                        with chunk_col1:
                            st.markdown(
                                f"**Chunk {chunk['chunk_index']}** "
                                f"({len(chunk['content'])} ký tự)\n\n{preview}"
                            )
                        with chunk_col2:
                            if st.button(
                                "🗑",
                                key=f"delchunk_{chunk['point_id']}",
                                help="Xóa chunk này khỏi Qdrant (file gốc giữ nguyên).",
                            ):
                                try:
                                    knowledge.delete_chunk(chunk["point_id"])
                                    set_knowledge_notice(
                                        "success",
                                        f"Đã xóa chunk {chunk['chunk_index']} "
                                        f"của {source}.",
                                    )
                                except Exception as exc:
                                    set_knowledge_notice(
                                        "error", f"Xóa chunk thất bại: {exc}"
                                    )
                                st.rerun()
                        st.divider()

    # ---------- Vùng nguy hiểm ----------
    st.markdown("### Vùng nguy hiểm")
    with st.expander("Xóa toàn bộ vector đã train"):
        st.warning(
            "Xóa sạch collection Qdrant (mọi vector). File gốc trong "
            "`data/knowledge/` giữ nguyên, có thể train lại sau. "
            "Dùng khi đổi embedding model hoặc muốn làm sạch index."
        )
        if not st.session_state.confirm_wipe_vectors:
            if st.button("🗑 Xóa toàn bộ vector", key="wipe_vectors"):
                st.session_state.confirm_wipe_vectors = True
                st.rerun()
        else:
            st.error("Chắc chắn xóa toàn bộ vector?")
            wipe_col1, wipe_col2 = st.columns(2)
            with wipe_col1:
                if st.button("✅ Xác nhận xóa hết", key="confirm_wipe"):
                    try:
                        knowledge.delete_all_vectors()
                        st.session_state.confirm_wipe_vectors = False
                        set_knowledge_notice(
                            "success", "Đã xóa toàn bộ vector trong Qdrant."
                        )
                    except Exception as exc:
                        set_knowledge_notice("error", f"Xóa thất bại: {exc}")
                    st.rerun()
            with wipe_col2:
                if st.button("Hủy", key="cancel_wipe"):
                    st.session_state.confirm_wipe_vectors = False
                    st.rerun()



# =========================
# Main
# =========================

render_sidebar()

if st.session_state.page == "📚 Quản lý Knowledge":
    render_knowledge_page()
else:
    render_chat_page()
