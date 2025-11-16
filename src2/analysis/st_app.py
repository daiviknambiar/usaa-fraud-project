import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter

# Try to import Supabase (optional)
try:
    from supabase import create_client
    from dotenv import load_dotenv
    load_dotenv()
    SUPABASE_AVAILABLE = True
except:
    SUPABASE_AVAILABLE = False


st.set_page_config(
    page_title="Fraud Analysis Dashboard",
    page_icon="🔍",
    layout="wide"
)

st.title("🔍 Fraud Analysis Dashboard")
st.markdown("### Analyzing fraud trends from press releases")


@st.cache_data
def load_latest_results():
    """Load the most recent analysis results from local files"""
    # Find the most recent results file
    json_files = list(Path('.').glob('fraud_analysis_results_*.json'))
    
    if not json_files:
        return None
    
    # Get the most recent file
    latest_file = max(json_files, key=os.path.getmtime)
    
    with open(latest_file, 'r') as f:
        results = json.load(f)
    
    # Also load the CSV for easier manipulation
    csv_files = list(Path('.').glob('fraud_analysis_results_*.csv'))
    if csv_files:
        latest_csv = max(csv_files, key=os.path.getmtime)
        df = pd.read_csv(latest_csv)
    else:
        df = None
    
    return {
        'json': results,
        'df': df,
        'timestamp': results.get('timestamp'),
        'source': 'local_files'
    }


@st.cache_resource
def load_from_database():
    """Try to load data from Supabase database"""
    if not SUPABASE_AVAILABLE:
        return None
    
    try:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url or not key:
            return None
        
        supabase = create_client(url, key)
        response = supabase.table('press_releases').select('*').execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            return {
                'df': df,
                'source': 'database',
                'total_articles': len(df)
            }
    except Exception as e:
        st.warning(f"Could not load from database: {e}")
        return None
    
    return None


# Main loading logic
data = load_latest_results()

if data is None:
    st.error("❌ No analysis results found!")
    st.markdown("""
    ### 🚀 Get Started
    
    Run the NLP pipeline to analyze your fraud articles:
    
    ```bash
    uv run nlp_pipeline_fixed.py
    ```
    
    This will create analysis files that this dashboard can display.
    """)
    st.stop()

# Sidebar
with st.sidebar:
    st.header("📊 Analysis Info")
    st.metric("Data Source", data['source'].replace('_', ' ').title())
    
    if data['timestamp']:
        st.metric("Last Updated", data['timestamp'])
    
    st.divider()
    
    # Refresh button
    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    st.divider()
    
    st.markdown("""
    ### 📋 Quick Actions
    - Run NLP pipeline for new data
    - Export results to CSV
    - Search for similar articles
    """)

# Main content
results = data['json']
df = data['df']

# Key Metrics
st.header("📈 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Total Articles",
        results['total_articles']
    )

with col2:
    st.metric(
        "Topics Discovered",
        results['summary']['total_topics']
    )

with col3:
    st.metric(
        "Articles Analyzed",
        results['summary']['articles_analyzed']
    )

with col4:
    unique_keywords = set()
    for keywords in results['keywords'].values():
        unique_keywords.update(keywords)
    st.metric(
        "Unique Keywords",
        len(unique_keywords)
    )

st.divider()

# Top 3 Fraud Trends
st.header("🔥 Top 3 Fraud Trends")

if 'trends' in results and results['trends']:
    for trend in results['trends']:
        with st.expander(f"#{trend['rank']} - {trend['name']}", expanded=True):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown(f"**{trend['description']}**")
                st.markdown("**Key Terms:**")
                
                # Display keywords as tags
                keywords_html = " ".join([
                    f'<span style="background-color: #1f77b4; color: white; padding: 5px 10px; border-radius: 5px; margin: 2px; display: inline-block;">{kw}</span>'
                    for kw in trend['keywords']
                ])
                st.markdown(keywords_html, unsafe_allow_html=True)
            
            with col2:
                st.metric("Occurrences", trend['count'])
else:
    st.warning("No trends data available. Run the NLP pipeline with the latest version.")

st.divider()

# Top Keywords Chart
st.header("🔑 Most Frequent Keywords")

# Aggregate all keywords
all_keywords = []
for keywords in results['keywords'].values():
    all_keywords.extend(keywords)

keyword_counts = Counter(all_keywords)
top_20_keywords = keyword_counts.most_common(20)

if top_20_keywords:
    keywords_df = pd.DataFrame(top_20_keywords, columns=['Keyword', 'Frequency'])
    
    fig = px.bar(
        keywords_df,
        x='Frequency',
        y='Keyword',
        orientation='h',
        title='Top 20 Keywords by Frequency',
        color='Frequency',
        color_continuous_scale='Blues'
    )
    fig.update_layout(height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No keyword data available")

st.divider()

# Topic Distribution
st.header("📊 Topic Distribution")

if results['topics']:
    topic_counts = Counter(results['topics'].values())
    
    topic_df = pd.DataFrame([
        {'Topic ID': topic_id, 'Article Count': count}
        for topic_id, count in topic_counts.items()
    ]).sort_values('Article Count', ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.pie(
            topic_df,
            values='Article Count',
            names='Topic ID',
            title='Articles by Topic'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            topic_df,
            x='Topic ID',
            y='Article Count',
            title='Topic Distribution',
            color='Article Count',
            color_continuous_scale='Viridis'
        )
        st.plotly_chart(fig, use_container_width=True)
else:
    st.warning("No topic data available")

st.divider()

# Articles Data Table
st.header("📄 Analyzed Articles")

if df is not None:
    # Add filters
    col1, col2 = st.columns(2)
    
    with col1:
        if 'topic_id' in df.columns:
            topics = ['All'] + sorted(df['topic_id'].dropna().unique().astype(str).tolist())
            selected_topic = st.selectbox("Filter by Topic", topics)
        else:
            selected_topic = 'All'
    
    with col2:
        search_term = st.text_input("Search in keywords", "")
    
    # Apply filters
    filtered_df = df.copy()
    
    if selected_topic != 'All':
        filtered_df = filtered_df[filtered_df['topic_id'].astype(str) == selected_topic]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['keywords'].str.contains(search_term, case=False, na=False)
        ]
    
    st.dataframe(
        filtered_df[['title', 'topic_id', 'keywords', 'has_embedding']],
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = filtered_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Filtered Data as CSV",
        data=csv,
        file_name=f"fraud_analysis_filtered_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
else:
    st.warning("No detailed article data available")

st.divider()

# Timeline (if date information available)
if df is not None and 'date' in df.columns:
    st.header("📅 Timeline Analysis")
    
    df['date'] = pd.to_datetime(df['date'])
    timeline_df = df.groupby(df['date'].dt.to_period('M')).size().reset_index()
    timeline_df.columns = ['Month', 'Article Count']
    timeline_df['Month'] = timeline_df['Month'].astype(str)
    
    fig = px.line(
        timeline_df,
        x='Month',
        y='Article Count',
        title='Articles Over Time',
        markers=True
    )
    st.plotly_chart(fig, use_container_width=True)

# Footer
st.divider()
st.markdown("""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>🔍 Fraud Analysis Dashboard | Powered by BERTopic, KeyBERT, and Streamlit</p>
    <p>Last analysis: {}</p>
</div>
""".format(results.get('timestamp', 'Unknown')), unsafe_allow_html=True)