import streamlit as st
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

# Custom Premium Styling
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
</style>
""", unsafe_allow_html=True)

# Initialize Session State values
if "messages" not in st.session_state:
    st.session_state.messages = []
if "force_refresh" not in st.session_state:
    st.session_state.force_refresh = False

# Sidebar Configuration
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/eagle.png", width=64)
    st.title("BI Controls")
    st.markdown("---")

    # Refresh data button
    if st.button("🔄 Refresh data from monday.com", use_container_width=True):
        st.session_state.force_refresh = True
        st.toast("Refreshing data pipeline...", icon="🔄")

    st.markdown("---")
    st.subheader("📊 Leadership BI Actions")
    if st.button("👑 Prepare Leadership Update", use_container_width=True):
        # Insert a chat query message to execute leadership tool
        st.session_state.messages.append({
            "role": "user", 
            "content": "Prepare this week's leadership update report."
        })
        st.rerun()

    st.markdown("---")
    st.subheader("LLM Configuration")
    llm_provider = st.selectbox(
        "LLM Provider",
        ["openai", "anthropic"],
        index=0 if settings.LLM_PROVIDER == "openai" else 1
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
    # Reset refresh flag
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

    # Show message history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "data" in msg and msg["data"] is not None:
                st.dataframe(msg["data"], use_container_width=True)

    # If the last message is from user (e.g. from the quick action button click), trigger reply
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        user_query = st.session_state.messages[-1]["content"]
        with st.chat_message("assistant"):
            with st.spinner("BI Agent is executing query plans..."):
                response = orchestrator.answer_query(user_query)
                st.markdown(response["answer"])
                df_res = response.get("data")
                if df_res is not None:
                    st.dataframe(df_res, use_container_width=True)
                
                # Append assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "data": df_res
                })
        st.rerun()

    # Standard Chat Input
    if prompt := st.chat_input("Ask a question about deals or project executions..."):
        # Append user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate assistant response
        with st.chat_message("assistant"):
            with st.spinner("BI Agent is executing query plans..."):
                response = orchestrator.answer_query(prompt)
                st.markdown(response["answer"])
                df_res = response.get("data")
                if df_res is not None:
                    st.dataframe(df_res, use_container_width=True)

                # Save assistant message
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["answer"],
                    "data": df_res
                })

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
