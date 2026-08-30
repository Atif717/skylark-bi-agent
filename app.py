import streamlit as st
import pandas as pd
import sys
import os

# Ensure the workspace is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings
from agent.orchestrator import AgentOrchestrator
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
    /* Styling settings page and general background */
    .stApp {
        background: linear-gradient(135deg, #0a0f1d 0%, #07070f 100%);
        color: #e2e8f0;
    }
    .sidebar .sidebar-content {
        background-color: #0d1527;
    }
    h1, h2, h3 {
        color: #f8fafc;
        font-family: 'Outfit', sans-serif;
    }
    .card {
        background: rgba(30, 41, 59, 0.4);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
    }
    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        color: #38bdf8;
    }
    .metric-label {
        font-size: 0.875rem;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# Sidebar settings override
with st.sidebar:
    st.image("https://img.icons8.com/nolan/96/eagle.png", width=64)
    st.title("Settings")
    st.markdown("---")
    
    st.subheader("LLM Configuration")
    llm_provider = st.selectbox(
        "LLM Provider",
        ["openai", "anthropic"],
        index=0 if settings.LLM_PROVIDER == "openai" else 1
    )
    llm_model = st.text_input("LLM Model", value=settings.LLM_MODEL)
    
    st.subheader("Monday.com Settings")
    deals_board = st.text_input("Deals Board ID", value=settings.DEALS_BOARD_ID)
    work_orders_board = st.text_input("Work Orders Board ID", value=settings.WORK_ORDERS_BOARD_ID)
    
    st.markdown("---")
    st.info("💡 Make sure to set actual tokens in your `.env` file to query real Monday.com boards.")

# Initialize Orchestrator
orchestrator = AgentOrchestrator(
    provider=llm_provider,
    model=llm_model,
    deals_board_id=deals_board,
    work_orders_board_id=work_orders_board
)

# Header Section
st.title("🦅 Skylark BI Assistant")
st.caption("Natural Language Interface for Monday.com Deals & Work Orders")

# Tabs for chat, data preview, and quality
tab1, tab2, tab3 = st.tabs(["💬 Chat Assistant", "📊 Data Preview", "🛡️ Data Quality Check"])

with tab1:
    st.markdown("### Ask questions about Deals and Work Orders")
    st.write("Example queries: *'What is the total value of our open deals?'*, *'Are there any delayed work orders?'*, *'Join our deals and work orders to show value by status.'*")
    
    # Initialize message history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    # Render messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "data" in msg and msg["data"] is not None:
                st.dataframe(msg["data"], use_container_width=True)

    # User Input
    if user_query := st.chat_input("Enter your BI question..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)
            
        # Display assistant thinking & generate response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing data and generating answer..."):
                response = orchestrator.answer_query(user_query)
                st.markdown(response["answer"])
                
                # Check if there is data returned by tools
                df_result = response.get("data")
                if df_result is not None:
                    st.dataframe(df_result, use_container_width=True)
                    
            # Save assistant message
            st.session_state.messages.append({
                "role": "assistant",
                "content": response["answer"],
                "data": df_result
            })

with tab2:
    st.markdown("### Raw Board Previews (Cached / Mock data)")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Deals Board")
        try:
            deals_df = orchestrator.get_deals_dataframe()
            st.metric("Total Deals Count", len(deals_df))
            st.dataframe(deals_df.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Error loading Deals: {e}")
            
    with col2:
        st.subheader("Work Orders Board")
        try:
            wo_df = orchestrator.get_work_orders_dataframe()
            st.metric("Total Work Orders Count", len(wo_df))
            st.dataframe(wo_df.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"Error loading Work Orders: {e}")

with tab3:
    st.markdown("### Data Quality Diagnostic Logs")
    st.write("Ensures schemas are consistent and identifies missing or invalid data points.")
    
    try:
        deals_df = orchestrator.get_deals_dataframe()
        wo_df = orchestrator.get_work_orders_dataframe()
        
        deals_quality = check_data_quality(deals_df, "Deals Board")
        wo_quality = check_data_quality(wo_df, "Work Orders Board")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"#### {deals_quality['name']}")
            st.write(f"**Missing Values Summary:**")
            st.write(deals_quality["missing_percentages"])
            st.write(f"**Row Count:** {deals_quality['total_rows']}")
            if deals_quality["quality_flags"]:
                st.warning("⚠️ Flags found:")
                for flag in deals_quality["quality_flags"]:
                    st.write(f"- {flag}")
            else:
                st.success("✅ No structural quality issues flagged.")
                
        with col2:
            st.markdown(f"#### {wo_quality['name']}")
            st.write(f"**Missing Values Summary:**")
            st.write(wo_quality["missing_percentages"])
            st.write(f"**Row Count:** {wo_quality['total_rows']}")
            if wo_quality["quality_flags"]:
                st.warning("⚠️ Flags found:")
                for flag in wo_quality["quality_flags"]:
                    st.write(f"- {flag}")
            else:
                st.success("✅ No structural quality issues flagged.")
    except Exception as e:
        st.error(f"Error checking data quality: {e}")
