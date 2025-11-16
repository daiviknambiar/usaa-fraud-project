# dashboard/app.py
import streamlit as st
from supabase import create_client
import plotly.express as px
import pandas as pd

st.set_page_config(page_title="FTC Fraud Insights", layout="wide")

# Initialize Supabase
supabase = create_client("SUPABASE_URL", "SUPABASE_KEY")

# Sidebar
st.sidebar.title("FTC Press Release Analysis")
page = st.sidebar.radio("Navigate", [
    "Overview",
    "Topic Explorer", 
    "Semantic Search",
    "Entity Tracker",
    "Trends"
])

if page == "Overview":
    st.title("📊 FTC Fraud Insights Dashboard")
    
    # Fetch summary stats from Supabase
    total_articles = supabase.table('press_releases').select('id', count='exact').execute()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Articles", total_articles.count)
    
    # Topic distribution
    topics = supabase.table('topics').select('*').execute()
    df_topics = pd.DataFrame(topics.data)
    
    fig = px.bar(df_topics, x='topic_name', y='article_count',
                 title="Articles by Topic")
    st.plotly_chart(fig)

elif page == "Topic Explorer":
    st.title("🔍 Topic Explorer")
    
    # Get all topics
    topics = supabase.table('topics').select('*').execute()
    topic_names = [t['topic_name'] for t in topics.data]
    
    selected_topic = st.selectbox("Select Topic", topic_names)
    
    # Get articles for this topic
    topic_id = next(t['id'] for t in topics.data if t['topic_name'] == selected_topic)
    
    articles = supabase.rpc('get_articles_by_topic', {'topic_id': topic_id}).execute()
    
    for article in articles.data:
        with st.expander(article['title']):
            st.write(f"**Date:** {article['published_date']}")
            st.write(article['summary'])
            st.link_button("Read Full Article", article['url'])

elif page == "Semantic Search":
    st.title("🔎 Semantic Search")
    
    query = st.text_input("Search articles (natural language)")
    
    if st.button("Search") and query:
        searcher = SemanticSearch()
        results = searcher.search(query)
        
        st.write(f"Found {len(results)} relevant articles:")
        
        for result in results:
            with st.expander(f"{result['title']} (Similarity: {result['similarity']:.2f})"):
                st.write(result['summary'])

elif page == "Entity Tracker":
    st.title("🏢 Entity Tracker")
    
    # Most mentioned companies
    companies = supabase.table('entities')\
        .select('entity_text, entity_type')\
        .eq('entity_type', 'ORG')\
        .execute()
    
    df = pd.DataFrame(companies.data)
    company_counts = df['entity_text'].value_counts().head(20)
    
    fig = px.bar(x=company_counts.index, y=company_counts.values,
                 title="Most Mentioned Organizations")
    st.plotly_chart(fig)
    
    # Penalty amounts
    penalties = supabase.table('entities')\
        .select('entity_text, article_id')\
        .eq('entity_type', 'MONEY')\
        .execute()
    
    st.subheader("Recent Penalties")
    st.dataframe(penalties.data)

elif page == "Trends":
    st.title("📈 Trends Over Time")
    
    # Articles per month
    articles = supabase.table('press_releases')\
        .select('published_date')\
        .execute()
    
    df = pd.DataFrame(articles.data)
    df['published_date'] = pd.to_datetime(df['published_date'])
    df['month'] = df['published_date'].dt.to_period('M')
    
    monthly_counts = df.groupby('month').size()
    
    fig = px.line(x=monthly_counts.index.astype(str), y=monthly_counts.values,
                  title="Articles Published Over Time")
    st.plotly_chart(fig)
