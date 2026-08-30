import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import os

# Ensure workspace is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from agent.orchestrator import AgentOrchestrator, InSessionCache
from data_processing.quality import check_data_quality

# Page Configuration
st.set_page_config(
    page_title="Skylark BI Agent",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #090d1a 0%, #05050c 100%);
        color: #f1f5f9;
    }
    .sidebar .sidebar-content {
        background-color: #0b132b;
    }
    h1, h2, h3 {
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
    }
    .card-panel {
        background: rgba(30, 41, 59, 0.45);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
    }
    [data-testid="stMain"] {
        scroll-behavior: smooth;
    }
</style>
""", unsafe_allow_html=True)


def scroll_to_bottom():
    """
    Scrolls the chat container to the bottom.
    Must use components.html (real iframe) — st.markdown's <script> tags
    are inserted via innerHTML and browsers never execute those.

    The hidden scroll-nonce comment (tied to message count) forces the
    injected HTML to be unique on every rerun. Without it, Streamlit
    detects identical content and reuses the same iframe instead of
    reloading it, so the <script> only ever fires on the very first run.
    """
    msg_count = len(st.session_state.get("messages", []))
    components.html(
        f"""
        <!-- scroll-nonce:{msg_count} -->
        <script>
            function scrollToBottom() {{
                const doc = window.parent.document;
                const container = doc.querySelector('[data-testid="stMain"]')
                                || doc.querySelector('section.main');
                if (container) {{
                    container.scrollTo({{ top: container.scrollHeight, behavior: 'smooth' }});
                }}
            }}
            setTimeout(scrollToBottom, 100);
            setTimeout(scrollToBottom, 350);
        </script>
        """,
        height=0,
    )


# Initialize Session State values
if "messages" not in st.session_state:
    st.session_state.messages = []
if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False

# Sidebar Configuration
with st.sidebar:
    st.markdown(
        "<div style='font-size:48px; line-height:1; margin-bottom:4px;'>🦅</div>",
        unsafe_allow_html=True
    )
    st.title("BI Controls")
    st.markdown("---")

    # Refresh data button
    if st.button("🔄 Refresh data from monday.com", use_container_width=True):
        st.session_state.force_refresh = True
        st.toast("Refreshing data pipeline...", icon="🔄")

    st.markdown("---")
    st.subheader("📊 Leadership BI Actions")
    if st.button("👑 Prepare Leadership Update", use_container_width=True):
        st.session_state.messages.append({
            "role": "user",
            "content": "Prepare this week's leadership update report."
        })
        st.rerun()

    st.markdown("---")
    st.subheader("LLM Configuration")
    providers = ["openai", "groq", "anthropic"]
    default_idx = providers.index(settings.LLM_PROVIDER) if settings.LLM_PROVIDER in providers else 0
    llm_provider = st.selectbox(
        "LLM Provider",
        providers,
        index=default_idx
    )
    llm_model = st.text_input("LLM Model", value=settings.LLM_MODEL)

    st.markdown("---")
    st.caption("Active Board IDs:")
    st.caption(f"Deals: `{settings.DEALS_BOARD_ID}`")
    st.caption(f"Work Orders: `{settings.WORK_ORDERS_BOARD_ID}`")

# Initialize Orchestrator
orchestrator = AgentOrchestrator(
    provider=llm_provider,
    model=llm_model,
    deals_board_id=settings.DEALS_BOARD_ID,
    work_orders_board_id=settings.WORK_ORDERS_BOARD_ID
)

# Fetch cached DataFrames from session state
try:
    deals_df, wo_df = InSessionCache.get_dataframes(
        orchestrator=orchestrator,
        force_refresh=st.session_state.force_refresh
    )
    st.session_state.force_refresh = False
except Exception as e:
    st.error(f"Error loading database boards: {e}")
    deals_df, wo_df = pd.DataFrame(), pd.DataFrame()

# Main Interface
st.title("🦅 Skylark BI Assistant")
st.caption("Conversational AI interface built for Monday.com boards analysis")

tab_chat, tab_preview, tab_quality = st.tabs(["💬 BI Assistant Chat", "📊 Data Previews", "🛡️ Diagnostics & Quality"])

with tab_chat:
    st.markdown("### Ask any business intelligence question")
    st.caption("e.g., 'What is the sum of deal values in the Mining sector?', 'Join our boards to show open deals linked to ongoing work orders', 'Prepare a leadership summary'")

    # Display Message History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "data" in msg and msg["data"] is not None:
                st.dataframe(msg["data"], use_container_width=True)

    # Handle quick-action trigger if last message was from user (e.g. sidebar buttons)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_query = st.session_state.messages[-1]["content"]

        # Only answer if assistant has not already appended a response
        if len(st.session_state.messages) % 2 != 0:
            with st.chat_message("assistant"):
                with st.spinner("BI Agent is executing query plans..."):
                    response = orchestrator.answer_query(user_query)
                    st.markdown(response["answer"])
                    df_res = response.get("data")
                    if df_res is not None:
                        st.dataframe(df_res, use_container_width=True)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response["answer"],
                        "data": df_res
                    })
            st.rerun()

with tab_preview:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Deals Board Data")
        st.metric("Total Deal Items", len(deals_df))
        st.dataframe(deals_df, use_container_width=True)

    with col2:
        st.subheader("Work Orders Board Data")
        st.metric("Total Work Order Items", len(wo_df))
        st.dataframe(wo_df, use_container_width=True)

with tab_quality:
    st.markdown("### 🛡️ Data Quality Diagnostics Panel")
    st.write("Scans all columns to report missing, invalid, or coerced data entries.")

    if not deals_df.empty and not wo_df.empty:
        deals_quality = check_data_quality(deals_df, "Deals Board")
        wo_quality = check_data_quality(wo_df, "Work Orders Board")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### {deals_quality['name']}")
            st.write(f"Total processed rows: `{deals_quality['total_rows']}`")
            if deals_quality["reports"]:
                for r in deals_quality["reports"]:
                    st.warning(f"⚠️ {r}")
            else:
                st.success("✅ 100% data completion. No issues found.")

        with col2:
            st.markdown(f"#### {wo_quality['name']}")
            st.write(f"Total processed rows: `{wo_quality['total_rows']}`")
            if wo_quality["reports"]:
                for r in wo_quality["reports"]:
                    st.warning(f"⚠️ {r}")
            else:
                st.success("✅ 100% data completion. No issues found.")
    else:
        st.info("No data available for quality scans. Check your Monday.com setup configuration.")

# Pinned Bottom Chat Input
if prompt := st.chat_input("Ask a question about deals or project executions..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with tab_chat:
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("BI Agent is executing query plans..."):
                response = orchestrator.answer_query(prompt)
                st.markdown(response["answer"])
                df_res = response.get("data")
                if df_res is not None:
                    st.dataframe(df_res, use_container_width=True)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "data": df_res
                })
    st.rerun()

# Single autoscroll call, executed after everything above has rendered
# for this run (whole history + any newly appended message).
scroll_to_bottom()