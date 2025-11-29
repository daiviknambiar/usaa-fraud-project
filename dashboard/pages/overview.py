import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

def render(loader):
    """Render the overview dashboard page"""
    
    st.markdown('<div class="main-header">📊 Fraud Intelligence Overview</div>', unsafe_allow_html=True)
    st.markdown("Real-time monitoring and analysis of fraud-related intelligence")
    
    # Load data with filters
    filters = st.session_state.get('filters', {})
    df = loader.load_articles(filters)
    
    if len(df) == 0:
        st.warning("⚠️ No data available. Please check your filters or run the scrapers to collect data.")
        st.info("To collect data, run: `python main.py all`")
        return
    
    # Summary statistics
    stats = loader.get_summary_stats(df)
    
    # Metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="📰 Total Articles",
            value=f"{stats['total_articles']:,}",
            delta=None
        )
    
    with col2:
        st.metric(
            label="⚠️ High Risk Cases",
            value=f"{stats['high_risk_count']:,}",
            delta=f"{(stats['high_risk_count']/stats['total_articles']*100):.1f}%" if stats['total_articles'] > 0 else "0%"
        )
    
    with col3:
        st.metric(
            label="📊 Avg Fraud Score",
            value=f"{stats['avg_fraud_score']:.2f}",
            delta=None
        )
    
    with col4:
        st.metric(
            label="🔍 Data Sources",
            value=stats['sources_count'],
            delta=None
        )
    
    st.markdown("---")
    
    # Two-column layout for charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Articles Published Over Time")
        
        # Time series frequency selector
        freq_option = st.selectbox(
            "Aggregation",
            options=['Daily', 'Weekly', 'Monthly'],
            index=1,
            key='time_freq'
        )
        
        freq_map = {'Daily': 'D', 'Weekly': 'W', 'Monthly': 'M'}
        time_series = loader.get_time_series_data(df, freq=freq_map[freq_option])
        
        if len(time_series) > 0:
            fig = go.Figure()
            
            # Article count
            fig.add_trace(go.Scatter(
                x=time_series['date'],
                y=time_series['count'],
                name='Article Count',
                mode='lines+markers',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=6)
            ))
            
            # Average fraud score (secondary axis)
            fig.add_trace(go.Scatter(
                x=time_series['date'],
                y=time_series['avg_fraud_score'],
                name='Avg Fraud Score',
                mode='lines',
                line=dict(color='#ff7f0e', width=2, dash='dash'),
                yaxis='y2'
            ))
            
            fig.update_layout(
                xaxis_title='Date',
                yaxis_title='Number of Articles',
                yaxis2=dict(
                    title='Average Fraud Score',
                    overlaying='y',
                    side='right'
                ),
                hovermode='x unified',
                height=400,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No time series data available")
    
    with col2:
        st.subheader("📊 Articles by Source")
        
        if 'source' in df.columns:
            source_counts = df['source'].value_counts().reset_index()
            source_counts.columns = ['source', 'count']
            
            # Create readable source names
            source_map = {
                'ftc_press': 'FTC Press Releases',
                'ftc_legal': 'FTC Legal Cases',
                'ftc_scams': 'FTC Consumer Scams'
            }
            source_counts['source_display'] = source_counts['source'].map(
                lambda x: source_map.get(x, x)
            )
            
            fig = px.pie(
                source_counts,
                values='count',
                names='source_display',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=400, showlegend=False)
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Source data not available")
    
    st.markdown("---")
    
    # Second row of visualizations
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🎯 Fraud Score Distribution")
        
        if 'fraud_score' in df.columns:
            fig = px.histogram(
                df,
                x='fraud_score',
                nbins=20,
                color_discrete_sequence=['#1f77b4'],
                labels={'fraud_score': 'Fraud Score', 'count': 'Number of Articles'}
            )
            
            # Add vertical line for high-risk threshold
            fig.add_vline(
                x=5.0,
                line_dash="dash",
                line_color="red",
                annotation_text="High Risk Threshold",
                annotation_position="top"
            )
            
            fig.update_layout(
                xaxis_title='Fraud Score',
                yaxis_title='Number of Articles',
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Fraud score data not available")
    
    with col2:
        st.subheader("🔤 Top Fraud Keywords")
        
        keywords_df = loader.get_top_keywords(df, n=15)
        
        if len(keywords_df) > 0:
            fig = px.bar(
                keywords_df,
                x='count',
                y='keyword',
                orientation='h',
                color='count',
                color_continuous_scale='Blues',
                labels={'count': 'Frequency', 'keyword': 'Keyword'}
            )
            
            fig.update_layout(
                height=400,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No keyword data available")
    
    st.markdown("---")
    
    # Recent high-risk alerts
    st.subheader("🚨 Recent High-Risk Alerts")
    
    high_risk_df = df[df['fraud_score'] >= 5.0].copy()
    
    if len(high_risk_df) > 0:
        # Sort by date, most recent first
        if 'published_at' in high_risk_df.columns:
            high_risk_df = high_risk_df.sort_values('published_at', ascending=False)
        
        # Show top 5
        for idx, row in high_risk_df.head(5).iterrows():
            with st.expander(f"⚠️ {row['title'][:100]}..." if len(row['title']) > 100 else f"⚠️ {row['title']}"):
                col1, col2, col3 = st.columns([2, 1, 1])
                
                with col1:
                    st.write(f"**Source:** {row.get('source', 'Unknown')}")
                    if 'published_at' in row and row['published_at']:
                        st.write(f"**Published:** {row['published_at'].strftime('%Y-%m-%d')}")
                
                with col2:
                    st.metric("Fraud Score", f"{row['fraud_score']:.1f}")
                
                with col3:
                    st.metric("Keyword Hits", int(row.get('fraud_hits', 0)))
                
                st.markdown("---")
                
                # Preview body (first 300 chars)
                body_preview = row.get('body', '')[:300] + "..." if len(row.get('body', '')) > 300 else row.get('body', '')
                st.write(body_preview)
                
                if 'url' in row and row['url']:
                    st.markdown(f"[🔗 Read Full Article]({row['url']})")
    else:
        st.info("No high-risk alerts in the current data range")
    
    # Export data button
    st.markdown("---")
    st.subheader("💾 Export Data")
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"fraud_intelligence_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )