import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from collections import Counter
import re

def render(loader):
    """Render the analytics page"""
    
    st.markdown('<div class="main-header">📈 Advanced Analytics</div>', unsafe_allow_html=True)
    st.markdown("Deep dive into fraud patterns and trends")
    
    # Load data
    filters = st.session_state.get('filters', {})
    df = loader.load_articles(filters)
    
    if len(df) == 0:
        st.warning("⚠️ No data available for analysis.")
        return
    
    # Analysis type selector
    analysis_type = st.selectbox(
        "Select Analysis Type",
        ["Trend Analysis", "Keyword Analysis", "Source Comparison", "Fraud Category Breakdown"]
    )
    
    st.markdown("---")
    
    if analysis_type == "Trend Analysis":
        render_trend_analysis(df, loader)
    elif analysis_type == "Keyword Analysis":
        render_keyword_analysis(df, loader)
    elif analysis_type == "Source Comparison":
        render_source_comparison(df)
    elif analysis_type == "Fraud Category Breakdown":
        render_fraud_categories(df)

def render_trend_analysis(df, loader):
    """Render trend analysis visualizations"""
    
    st.subheader("📊 Trend Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        time_freq = st.selectbox("Time Aggregation", ["Daily", "Weekly", "Monthly"], index=1)
    
    with col2:
        metric_choice = st.selectbox("Metric", ["Article Count", "Average Fraud Score", "Both"])
    
    freq_map = {'Daily': 'D', 'Weekly': 'W', 'Monthly': 'M'}
    time_series = loader.get_time_series_data(df, freq=freq_map[time_freq])
    
    if len(time_series) > 0:
        fig = go.Figure()
        
        if metric_choice in ["Article Count", "Both"]:
            fig.add_trace(go.Scatter(
                x=time_series['date'],
                y=time_series['count'],
                name='Article Count',
                mode='lines+markers',
                line=dict(color='#1f77b4', width=3),
                marker=dict(size=8)
            ))
        
        if metric_choice in ["Average Fraud Score", "Both"]:
            y_axis = 'y2' if metric_choice == "Both" else 'y'
            fig.add_trace(go.Scatter(
                x=time_series['date'],
                y=time_series['avg_fraud_score'],
                name='Avg Fraud Score',
                mode='lines+markers',
                line=dict(color='#ff7f0e', width=3),
                marker=dict(size=8),
                yaxis=y_axis
            ))
        
        layout_config = {
            'xaxis_title': 'Date',
            'height': 500,
            'hovermode': 'x unified'
        }
        
        if metric_choice == "Both":
            layout_config.update({
                'yaxis_title': 'Number of Articles',
                'yaxis2': dict(
                    title='Average Fraud Score',
                    overlaying='y',
                    side='right'
                )
            })
        elif metric_choice == "Article Count":
            layout_config['yaxis_title'] = 'Number of Articles'
        else:
            layout_config['yaxis_title'] = 'Average Fraud Score'
        
        fig.update_layout(**layout_config)
        st.plotly_chart(fig, use_container_width=True)
        
        # Trend insights
        st.markdown("### 📝 Insights")
        
        if len(time_series) >= 2:
            recent_avg = time_series.tail(5)['count'].mean()
            older_avg = time_series.head(5)['count'].mean() if len(time_series) >= 10 else time_series['count'].mean()
            
            change_pct = ((recent_avg - older_avg) / older_avg * 100) if older_avg > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Recent Avg (last 5 periods)",
                    f"{recent_avg:.1f}",
                    f"{change_pct:+.1f}%"
                )
            
            with col2:
                peak_date = time_series.loc[time_series['count'].idxmax(), 'date']
                peak_count = time_series['count'].max()
                st.metric("Peak Period", f"{peak_date.strftime('%Y-%m-%d')}", f"{int(peak_count)} articles")
            
            with col3:
                avg_score = time_series['avg_fraud_score'].mean()
                st.metric("Overall Avg Fraud Score", f"{avg_score:.2f}")

def render_keyword_analysis(df, loader):
    """Render keyword analysis"""
    
    st.subheader("🔤 Keyword Analysis")
    
    # Top keywords
    n_keywords = st.slider("Number of keywords to display", 10, 50, 20)
    keywords_df = loader.get_top_keywords(df, n=n_keywords)
    
    if len(keywords_df) > 0:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("#### Top Keywords")
            
            fig = px.bar(
                keywords_df.head(20),
                x='count',
                y='keyword',
                orientation='h',
                color='count',
                color_continuous_scale='Viridis',
                labels={'count': 'Frequency', 'keyword': 'Keyword'}
            )
            
            fig.update_layout(
                height=600,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Keyword Stats")
            st.dataframe(
                keywords_df,
                use_container_width=True,
                height=600
            )
        
        # Keyword co-occurrence
        st.markdown("---")
        st.markdown("#### 🔗 Keyword Co-occurrence")
        
        st.info("This shows which fraud-related keywords frequently appear together in articles")
        
        # Simple co-occurrence matrix for top keywords
        top_keywords = keywords_df.head(10)['keyword'].tolist()
        cooccurrence = calculate_cooccurrence(df, top_keywords)
        
        if cooccurrence is not None:
            fig = px.imshow(
                cooccurrence,
                labels=dict(x="Keyword", y="Keyword", color="Co-occurrences"),
                x=top_keywords,
                y=top_keywords,
                color_continuous_scale='Blues',
                aspect='auto'
            )
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

def calculate_cooccurrence(df, keywords):
    """Calculate keyword co-occurrence matrix"""
    if len(df) == 0:
        return None
    
    n = len(keywords)
    cooccurrence = [[0 for _ in range(n)] for _ in range(n)]
    
    for _, row in df.iterrows():
        body_lower = row.get('body', '').lower()
        
        # Check which keywords appear in this article
        present_keywords = [i for i, kw in enumerate(keywords) if kw in body_lower]
        
        # Increment co-occurrence for all pairs
        for i in present_keywords:
            for j in present_keywords:
                cooccurrence[i][j] += 1
    
    return cooccurrence

def render_source_comparison(df):
    """Render source comparison analysis"""
    
    st.subheader("📰 Source Comparison")
    
    if 'source' not in df.columns:
        st.warning("Source information not available")
        return
    
    source_stats = df.groupby('source').agg({
        'title': 'count',
        'fraud_score': ['mean', 'max', 'min']
    }).reset_index()
    
    source_stats.columns = ['source', 'count', 'avg_score', 'max_score', 'min_score']
    
    # Readable source names
    source_map = {
        'ftc_press': 'FTC Press Releases',
        'ftc_legal': 'FTC Legal Cases',
        'ftc_scams': 'FTC Consumer Scams'
    }
    source_stats['source_display'] = source_stats['source'].map(lambda x: source_map.get(x, x))
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Article Count by Source")
        fig = px.bar(
            source_stats,
            x='source_display',
            y='count',
            color='count',
            color_continuous_scale='Blues',
            labels={'source_display': 'Source', 'count': 'Number of Articles'}
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Average Fraud Score by Source")
        fig = px.bar(
            source_stats,
            x='source_display',
            y='avg_score',
            color='avg_score',
            color_continuous_scale='Reds',
            labels={'source_display': 'Source', 'avg_score': 'Avg Fraud Score'}
        )
        fig.update_layout(height=400, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    st.markdown("#### 📊 Detailed Source Statistics")
    st.dataframe(
        source_stats[['source_display', 'count', 'avg_score', 'max_score', 'min_score']],
        use_container_width=True,
        hide_index=True
    )

def render_fraud_categories(df):
    """Render fraud category analysis"""
    
    st.subheader("🏷️ Fraud Category Breakdown")
    
    st.info("This analysis attempts to categorize articles based on fraud type keywords")
    
    # Define fraud categories and their keywords
    categories = {
        'Identity Theft': ['identity', 'theft', 'personal information', 'ssn', 'social security'],
        'Phishing': ['phishing', 'email scam', 'fake email', 'spoofing'],
        'Investment Scam': ['investment', 'ponzi', 'pyramid', 'cryptocurrency', 'bitcoin'],
        'Credit Card Fraud': ['credit card', 'debit card', 'card fraud', 'unauthorized charge'],
        'Wire Transfer Fraud': ['wire transfer', 'wire fraud', 'money transfer'],
        'Ransomware': ['ransomware', 'malware', 'encryption', 'ransom'],
        'Business Email Compromise': ['bec', 'business email', 'ceo fraud', 'executive'],
        'Romance Scam': ['romance', 'dating', 'online relationship'],
        'Tech Support Scam': ['tech support', 'computer repair', 'virus warning']
    }
    
    # Categorize articles
    category_counts = {cat: 0 for cat in categories.keys()}
    
    for _, row in df.iterrows():
        body_lower = row.get('body', '').lower()
        title_lower = row.get('title', '').lower()
        combined_text = body_lower + ' ' + title_lower
        
        for category, keywords in categories.items():
            if any(kw in combined_text for kw in keywords):
                category_counts[category] += 1
    
    # Create dataframe
    category_df = pd.DataFrame(
        list(category_counts.items()),
        columns=['Category', 'Count']
    ).sort_values('Count', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(
            category_df,
            x='Count',
            y='Category',
            orientation='h',
            color='Count',
            color_continuous_scale='Reds',
            labels={'Count': 'Number of Articles', 'Category': 'Fraud Category'}
        )
        
        fig.update_layout(
            height=500,
            showlegend=False,
            yaxis={'categoryorder': 'total ascending'}
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown("#### Category Counts")
        st.dataframe(category_df, use_container_width=True, hide_index=True)
        
        total_categorized = category_df['Count'].sum()
        st.metric("Total Categorizations", total_categorized)
        st.caption("Note: Articles can appear in multiple categories")