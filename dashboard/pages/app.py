import sys
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)
 

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import page modules directly
from dashboard.pages import overview, article_browser, analytics, upload_analyzer
from dashboard.utils.data_loader import DataLoader

# Page configuration
st.set_page_config(
    page_title="USAA Fraud Intelligence Dashboard",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
    }
    </style>
""", unsafe_allow_html=True)

def main():
    # Sidebar configuration
    st.sidebar.title("🔍 Fraud Intelligence")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["📊 Overview", "📰 Article Browser", "📈 Analytics", "📤 Upload & Analyze"],
        label_visibility="collapsed"
    )
    
    st.sidebar.markdown("---")
    
    # Sidebar filters (global)
    st.sidebar.subheader("Global Filters")
    
    # Initialize data loader
    @st.cache_resource
    def get_data_loader():
        return DataLoader()
    
    loader = get_data_loader()
    
    # Date range filter
    date_range = st.sidebar.date_input(
        "Date Range",
        value=(datetime.now() - timedelta(days=90), datetime.now()),
        max_value=datetime.now()
    )
    
    # Source filter
    sources = st.sidebar.multiselect(
        "Sources",
        options=["FTC Press Releases", "FTC Legal Cases", "FTC Consumer Scams", "All"],
        default=["All"]
    )
    
    # Fraud score threshold
    min_fraud_score = st.sidebar.slider(
        "Minimum Fraud Score",
        min_value=0.0,
        max_value=10.0,
        value=2.0,
        step=0.5
    )
    
    st.sidebar.markdown("---")
    st.sidebar.info(
        "**About**: This dashboard provides intelligence analysis "
        "of fraud-related content scraped from FTC sources."
    )
    
    # Store filters in session state
    if 'filters' not in st.session_state:
        st.session_state.filters = {}
    
    st.session_state.filters = {
        'date_range': date_range,
        'sources': sources,
        'min_fraud_score': min_fraud_score
    }
    
    # Route to appropriate page
    if page == "📊 Overview":
        overview.render(loader)
    elif page == "📰 Article Browser":
        article_browser.render(loader)
    elif page == "📈 Analytics":
        analytics.render(loader)
    elif page == "📤 Upload & Analyze":
        upload_analyzer.render(loader)

if __name__ == "__main__":
    main()