import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from collections import Counter
import re
import numpy as np
from pathlib import Path

def render(loader):
    """Render the enhanced analytics page"""
    
    st.markdown('<div class="main-header">📈 Advanced Analytics</div>', unsafe_allow_html=True)
    st.markdown("Deep dive into fraud patterns and insights")
    
    # Load data
    filters = st.session_state.get('filters', {})
    df = loader.load_articles(filters)
    
    if len(df) == 0:
        st.warning("⚠️ No data available for analysis.")
        return
    
    # Analysis tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Score Analysis", 
        "🔤 Keyword Insights", 
        "🗺️ Geographic", 
        "🌐 Network View",
        "🎯 Embeddings"
    ])
    
    with tab1:
        render_fraud_score_analysis(df)
    
    with tab2:
        render_keyword_analysis(df, loader)
    
    with tab3:
        render_geographic_analysis(df)
    
    with tab4:
        render_network_analysis(df)
    
    with tab5:
        render_embeddings_view(df)

def render_fraud_score_analysis(df):
    """Enhanced fraud score distribution analysis"""
    
    st.subheader("📊 Fraud Score Distribution")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Enhanced histogram with risk zones
        fig = go.Figure()
        
        fig.add_trace(go.Histogram(
            x=df['fraud_score'],
            nbinsx=30,
            name='Count',
            marker_color='#3498db',
            opacity=0.8,
            hovertemplate='Score: %{x}<br>Count: %{y}<extra></extra>'
        ))
        
        # Add background rectangles for risk zones
        fig.add_vrect(x0=0, x1=2, fillcolor="green", opacity=0.1, line_width=0, annotation_text="Low Risk")
        fig.add_vrect(x0=2, x1=5, fillcolor="orange", opacity=0.1, line_width=0, annotation_text="Medium Risk")
        fig.add_vrect(x0=5, x1=7, fillcolor="red", opacity=0.1, line_width=0, annotation_text="High Risk")
        fig.add_vrect(x0=7, x1=df['fraud_score'].max()+1, fillcolor="darkred", opacity=0.1, line_width=0, annotation_text="Critical")
        
        fig.update_layout(
            title="Distribution with Risk Zones",
            xaxis_title="Fraud Score",
            yaxis_title="Number of Articles",
            height=400,
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Risk category breakdown with counts
        risk_categories = pd.cut(df['fraud_score'], 
                                bins=[-np.inf, 2, 5, 7, np.inf],
                                labels=['Low (0-2)', 'Medium (2-5)', 'High (5-7)', 'Critical (7+)'])
        
        risk_counts = risk_categories.value_counts().sort_index()
        
        colors = ['#2ecc71', '#f39c12', '#e74c3c', '#8e44ad']
        
        fig = go.Figure(data=[go.Pie(
            labels=risk_counts.index,
            values=risk_counts.values,
            marker=dict(colors=colors),
            hole=0.4,
            textinfo='label+percent+value',
            hovertemplate='%{label}<br>Count: %{value}<br>Percent: %{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title="Risk Distribution by Category",
            height=400
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Statistics cards
    st.markdown("---")
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric("Mean", f"{df['fraud_score'].mean():.2f}")
    with col2:
        st.metric("Median", f"{df['fraud_score'].median():.2f}")
    with col3:
        st.metric("Std Dev", f"{df['fraud_score'].std():.2f}")
    with col4:
        st.metric("Min", f"{df['fraud_score'].min():.2f}")
    with col5:
        st.metric("Max", f"{df['fraud_score'].max():.2f}")
    with col6:
        st.metric("Range", f"{df['fraud_score'].max() - df['fraud_score'].min():.2f}")
    
    # Source comparison boxplot
    st.markdown("---")
    st.markdown("### 📦 Score Distribution by Source")
    
    fig = go.Figure()
    
    source_names = {
        'ftc_dnc': 'DNC Complaints',
        'ftc_press': 'Press Releases',
        'ftc_scams': 'Consumer Scams',
        'data-spotlight': 'Data Spotlight'
    }
    
    for source in df['source'].unique():
        source_data = df[df['source'] == source]['fraud_score']
        display_name = source_names.get(source, source)
        
        fig.add_trace(go.Box(
            y=source_data,
            name=display_name,
            boxmean='sd',
            marker_color='#3498db'
        ))
    
    fig.update_layout(
        yaxis_title="Fraud Score",
        xaxis_title="Source",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Violin plot for detailed distribution
    st.markdown("### 🎻 Detailed Score Distribution by Source")
    
    fig = go.Figure()
    
    for source in df['source'].unique():
        source_data = df[df['source'] == source]['fraud_score']
        display_name = source_names.get(source, source)
        
        fig.add_trace(go.Violin(
            y=source_data,
            name=display_name,
            box_visible=True,
            meanline_visible=True
        ))
    
    fig.update_layout(
        yaxis_title="Fraud Score",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def render_keyword_analysis(df, loader):
    """Enhanced keyword analysis"""
    
    st.subheader("🔤 Keyword Intelligence")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        n_keywords = st.slider("Top N Keywords", 10, 50, 20)
        chart_type = st.radio("Chart Type", ["Bar Chart", "Treemap", "Word Cloud"])
    
    keywords_df = loader.get_top_keywords(df, n=n_keywords)
    
    if len(keywords_df) > 0:
        with col2:
            if chart_type == "Bar Chart":
                fig = px.bar(
                    keywords_df.head(20),
                    x='count',
                    y='keyword',
                    orientation='h',
                    color='count',
                    color_continuous_scale='Reds',
                    labels={'count': 'Frequency', 'keyword': 'Keyword'},
                    title="Most Common Fraud Keywords"
                )
                fig.update_layout(
                    height=600,
                    yaxis={'categoryorder': 'total ascending'}
                )
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "Treemap":
                fig = px.treemap(
                    keywords_df.head(30),
                    path=['keyword'],
                    values='count',
                    color='count',
                    color_continuous_scale='Reds',
                    title="Keyword Frequency Treemap"
                )
                fig.update_layout(height=600)
                st.plotly_chart(fig, use_container_width=True)
            
            elif chart_type == "Word Cloud":
                st.info("📝 Keyword sizes represent frequency")
                # Create a scatter-based word cloud
                fig = go.Figure()
                
                # Position keywords randomly but deterministically
                np.random.seed(42)
                x_pos = np.random.randn(len(keywords_df))
                y_pos = np.random.randn(len(keywords_df))
                
                fig.add_trace(go.Scatter(
                    x=x_pos,
                    y=y_pos,
                    mode='text',
                    text=keywords_df['keyword'],
                    textfont=dict(
                        size=keywords_df['count'] / keywords_df['count'].max() * 50 + 10,
                        color=keywords_df['count']
                    ),
                    hovertemplate='%{text}<br>Count: %{marker.color}<extra></extra>',
                    marker=dict(
                        color=keywords_df['count'],
                        colorscale='Reds',
                        showscale=True
                    )
                ))
                
                fig.update_layout(
                    title="Fraud Keyword Cloud",
                    height=600,
                    xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
                    yaxis=dict(showgrid=False, showticklabels=False, zeroline=False)
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Keyword co-occurrence heatmap
        st.markdown("---")
        st.markdown("### 🔗 Keyword Co-occurrence Matrix")
        st.info("Shows which fraud keywords frequently appear together in the same article")
        
        top_keywords = keywords_df.head(10)['keyword'].tolist()
        cooccurrence = calculate_cooccurrence(df, top_keywords)
        
        if cooccurrence is not None:
            fig = px.imshow(
                cooccurrence,
                labels=dict(x="Keyword", y="Keyword", color="Co-occurrences"),
                x=top_keywords,
                y=top_keywords,
                color_continuous_scale='Blues',
                aspect='auto',
                text_auto=True
            )
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)

def calculate_cooccurrence(df, keywords):
    """Calculate keyword co-occurrence matrix"""
    if len(df) == 0:
        return None
    
    n = len(keywords)
    cooccurrence = np.zeros((n, n))
    
    for _, row in df.iterrows():
        # Convert to string to handle NaN/float values
        body = str(row.get('body', '')) if pd.notna(row.get('body')) else ''
        body_lower = body.lower()
        
        # Check which keywords appear in this article
        present_keywords = [i for i, kw in enumerate(keywords) if kw in body_lower]
        
        # Increment co-occurrence for all pairs
        for i in present_keywords:
            for j in present_keywords:
                cooccurrence[i][j] += 1
    
    return cooccurrence

def render_geographic_analysis(df):
    """Geographic analysis of fraud data"""
    
    st.subheader("🗺️ Geographic Distribution")
    
    # Extract location data from DNC complaints
    locations = []
    for _, row in df.iterrows():
        if 'metadata' in row and isinstance(row['metadata'], dict):
            location = row['metadata'].get('location', '')
            if location:
                locations.append(location)
        elif 'body' in row and pd.notna(row.get('body')):
            # Try to extract location from body
            body = str(row.get('body', ''))
            import re
            location_match = re.search(r'Location: ([^(]+)', body)
            if location_match:
                locations.append(location_match.group(1).strip())
    
    if locations:
        location_counts = Counter(locations)
        location_df = pd.DataFrame(location_counts.most_common(20), columns=['Location', 'Count'])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            fig = px.bar(
                location_df,
                x='Count',
                y='Location',
                orientation='h',
                title="Top 20 Locations by Complaint Volume",
                color='Count',
                color_continuous_scale='Reds'
            )
            fig.update_layout(height=600, yaxis={'categoryorder': 'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### Location Stats")
            st.metric("Total Unique Locations", len(location_counts))
            st.metric("Most Common", location_df.iloc[0]['Location'])
            st.metric("Top Location Count", int(location_df.iloc[0]['Count']))
            
            st.markdown("---")
            st.dataframe(location_df, use_container_width=True, height=400)
        


def render_network_analysis(df):
    """Network view of fraud types and relationships"""
    
    st.subheader("🌐 Fraud Type Network")
    
    st.info("This visualization shows how different fraud categories relate to each other based on keyword co-occurrence")
    
    # Define fraud categories
    categories = {
        'Identity Theft': ['identity', 'theft', 'personal information', 'ssn'],
        'Phishing': ['phishing', 'email scam', 'fake email'],
        'Investment': ['investment', 'ponzi', 'pyramid', 'cryptocurrency'],
        'Credit Card': ['credit card', 'debit card', 'unauthorized charge'],
        'Wire Transfer': ['wire transfer', 'wire fraud', 'money transfer'],
        'Ransomware': ['ransomware', 'malware', 'encryption'],
        'Romance Scam': ['romance', 'dating', 'relationship'],
        'Tech Support': ['tech support', 'computer repair', 'virus']
    }
    
    # Categorize articles
    article_categories = []
    for _, row in df.iterrows():
        # Convert to string to handle NaN/float values
        title = str(row.get('title', '')) if pd.notna(row.get('title')) else ''
        body = str(row.get('body', '')) if pd.notna(row.get('body')) else ''
        text = (title + ' ' + body).lower()
        
        article_cats = []
        for category, keywords in categories.items():
            if any(kw in text for kw in keywords):
                article_cats.append(category)
        article_categories.append(article_cats)
    
    # Calculate category co-occurrence
    cat_names = list(categories.keys())
    n_cats = len(cat_names)
    co_matrix = np.zeros((n_cats, n_cats))
    
    for cats in article_categories:
        for i, cat1 in enumerate(cat_names):
            for j, cat2 in enumerate(cat_names):
                if cat1 in cats and cat2 in cats:
                    co_matrix[i][j] += 1
    
    # Create network visualization using scatter plot
    fig = go.Figure()
    
    # Position nodes in a circle
    angles = np.linspace(0, 2*np.pi, n_cats, endpoint=False)
    x_pos = np.cos(angles)
    y_pos = np.sin(angles)
    
    # Add edges (connections) based on co-occurrence
    edge_trace = []
    threshold = np.percentile(co_matrix[co_matrix > 0], 50) if co_matrix.max() > 0 else 0
    
    for i in range(n_cats):
        for j in range(i+1, n_cats):
            if co_matrix[i][j] > threshold:
                edge_trace.append(
                    go.Scatter(
                        x=[x_pos[i], x_pos[j]],
                        y=[y_pos[i], y_pos[j]],
                        mode='lines',
                        line=dict(width=co_matrix[i][j]/co_matrix.max()*10, color='lightgray'),
                        hoverinfo='skip',
                        showlegend=False
                    )
                )
    
    # Add edges to plot
    for edge in edge_trace:
        fig.add_trace(edge)
    
    # Add nodes
    node_sizes = [sum(1 for cats in article_categories if cat in cats) for cat in cat_names]
    
    fig.add_trace(go.Scatter(
        x=x_pos,
        y=y_pos,
        mode='markers+text',
        marker=dict(
            size=[s*2 + 20 for s in node_sizes],
            color=node_sizes,
            colorscale='Reds',
            showscale=True,
            colorbar=dict(title="Article Count"),
            line=dict(width=2, color='white')
        ),
        text=cat_names,
        textposition='top center',
        textfont=dict(size=12, color='black'),
        hovertemplate='%{text}<br>Articles: %{marker.color}<extra></extra>'
    ))
    
    fig.update_layout(
        title="Fraud Category Network<br><sub>Node size = article count, Lines = co-occurrence</sub>",
        height=700,
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        showlegend=False,
        hovermode='closest'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Category breakdown table
    st.markdown("---")
    st.markdown("### 📊 Category Statistics")
    
    category_stats = []
    for cat in cat_names:
        count = sum(1 for cats in article_categories if cat in cats)
        category_stats.append({'Category': cat, 'Article Count': count})
    
    stats_df = pd.DataFrame(category_stats).sort_values('Article Count', ascending=False)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        fig = px.bar(
            stats_df,
            x='Article Count',
            y='Category',
            orientation='h',
            color='Article Count',
            color_continuous_scale='Reds',
            title="Articles per Fraud Category"
        )
        fig.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.dataframe(stats_df, use_container_width=True, hide_index=True, height=400)

def render_embeddings_view(df):
    """Display embeddings visualization"""
    
    st.subheader("🎯 Document Similarity Map (Embeddings)")
    
    st.info("""
    **What are embeddings?** Embeddings convert articles into numerical vectors that capture their meaning. 
    Articles with similar content will appear close together in this visualization.
    """)
    
    # Define paths to pre-generated images
    # Try both local and Modal deployment paths
    base_paths = ["visualizations", "/root/visualizations"]
    
    def find_file(filename):
        for base in base_paths:
            path = Path(base) / filename
            if path.exists():
                return path
        return None
    
    pca_2d_path = find_file("embeddings_2d_pca.png")
    tsne_2d_path = find_file("embeddings_2d_tsne.png")
    pca_3d_path = find_file("embeddings_3d_pca.png")
    tsne_3d_path = find_file("embeddings_3d_tsne.png")
    
    # Check if any visualization exists
    has_visualizations = any([
        pca_2d_path is not None,
        tsne_2d_path is not None,
        pca_3d_path is not None,
        tsne_3d_path is not None
    ])
    
    if not has_visualizations:
        st.warning("⚠️ No embedding visualizations found in the visualizations directory.")
        st.markdown("Please ensure the visualization PNG files are included in the deployment.")
        return
    
    st.success("✅ Embeddings visualizations loaded!")
    
    # Display 2D visualizations
    st.markdown("### 📊 2D Projections")
    st.markdown("These visualizations show fraud articles clustered by similarity in 2D space.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if pca_2d_path:
            st.markdown("#### PCA 2D Projection")
            st.markdown("*Principal Component Analysis - Linear dimensionality reduction*")
            st.image(str(pca_2d_path), use_container_width=True)
        else:
            st.info("PCA 2D visualization not available")
    
    with col2:
        if tsne_2d_path:
            st.markdown("#### t-SNE 2D Projection")
            st.markdown("*t-Distributed Stochastic Neighbor Embedding - Non-linear reduction*")
            st.image(str(tsne_2d_path), use_container_width=True)
        else:
            st.info("t-SNE 2D visualization not available")
    
    # Display 3D visualizations
    st.markdown("---")
    st.markdown("### 📐 3D Projections")
    st.markdown("These visualizations provide an additional dimension for exploring fraud patterns.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if pca_3d_path:
            st.markdown("#### PCA 3D Projection")
            st.image(str(pca_3d_path), use_container_width=True)
        else:
            st.info("PCA 3D visualization not available")
    
    with col2:
        if tsne_3d_path:
            st.markdown("#### t-SNE 3D Projection")
            st.image(str(tsne_3d_path), use_container_width=True)
        else:
            st.info("t-SNE 3D visualization not available")
    
    # Additional visualizations if they exist
    st.markdown("---")
    st.markdown("### 📈 Additional Insights")
    
    fraud_overview_path = find_file("fraud_overview.jpeg")
    fraud_score_path = find_file("fraud_score.png")
    high_risk_path = find_file("high-risk_alerts.jpeg")
    articles_published_path = find_file("articles_published.png")
    
    if fraud_overview_path or fraud_score_path:
        col1, col2 = st.columns(2)
        
        with col1:
            if fraud_overview_path:
                st.markdown("#### Fraud Overview")
                st.image(str(fraud_overview_path), use_container_width=True)
        
        with col2:
            if fraud_score_path:
                st.markdown("#### Fraud Score Distribution")
                st.image(str(fraud_score_path), use_container_width=True)
    
    if high_risk_path or articles_published_path:
        col1, col2 = st.columns(2)
        
        with col1:
            if high_risk_path:
                st.markdown("#### High-Risk Alerts")
                st.image(str(high_risk_path), use_container_width=True)
        
        with col2:
            if articles_published_path:
                st.markdown("#### Articles Published")
                st.image(str(articles_published_path), use_container_width=True)
    
    # Info about the visualizations
    st.markdown("---")
    st.markdown("""
    ### 📖 Understanding These Visualizations
    
    **What do the clusters mean?**
    - Points close together represent articles with similar fraud patterns and language
    - Different colors typically represent different data sources or fraud categories
    - Distinct clusters may indicate different types of fraud schemes
    
    **PCA vs t-SNE:**
    - **PCA**: Preserves global structure, faster, deterministic
    - **t-SNE**: Better at preserving local structure, reveals fine-grained patterns
    
    **How to use this:**
    - Look for tight clusters to identify common fraud patterns
    - Outliers may represent unique or emerging fraud schemes
    - Use this to understand relationships between different fraud cases
    """)