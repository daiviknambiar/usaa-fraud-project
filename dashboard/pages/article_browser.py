import streamlit as st
import pandas as pd

def render(loader):
    """Render the article browser page"""
    
    st.markdown('<div class="main-header">📰 Article Browser</div>', unsafe_allow_html=True)
    st.markdown("Search and explore fraud-related articles")
    
    # Load data with filters
    filters = st.session_state.get('filters', {})
    df = loader.load_articles(filters)
    
    if len(df) == 0:
        st.warning("⚠️ No articles found. Try adjusting your filters.")
        return
    
    # Search and filter controls
    st.markdown("### 🔍 Search & Filter")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_query = st.text_input(
            "Search articles by title or content",
            placeholder="Enter keywords...",
            label_visibility="collapsed"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            options=['Most Recent', 'Highest Fraud Score', 'Lowest Fraud Score', 'Title (A-Z)'],
            label_visibility="collapsed"
        )
    
    # Apply search filter
    filtered_df = df.copy()
    
    if search_query:
        search_lower = search_query.lower()
        mask = (
            filtered_df['title'].str.lower().str.contains(search_lower, na=False) |
            filtered_df['body'].str.lower().str.contains(search_lower, na=False)
        )
        filtered_df = filtered_df[mask]
    
    # Apply sorting
    if sort_by == 'Most Recent' and 'published_at' in filtered_df.columns:
        filtered_df = filtered_df.sort_values('published_at', ascending=False)
    elif sort_by == 'Highest Fraud Score':
        filtered_df = filtered_df.sort_values('fraud_score', ascending=False)
    elif sort_by == 'Lowest Fraud Score':
        filtered_df = filtered_df.sort_values('fraud_score', ascending=True)
    elif sort_by == 'Title (A-Z)':
        filtered_df = filtered_df.sort_values('title', ascending=True)
    
    # Results summary
    st.markdown(f"**Showing {len(filtered_df)} of {len(df)} articles**")
    
    if search_query:
        st.info(f"🔍 Search results for: \"{search_query}\"")
    
    st.markdown("---")
    
    # Pagination
    items_per_page = 10
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    
    total_pages = (len(filtered_df) - 1) // items_per_page + 1
    
    # Article list
    start_idx = st.session_state.current_page * items_per_page
    end_idx = min(start_idx + items_per_page, len(filtered_df))
    
    page_df = filtered_df.iloc[start_idx:end_idx]
    
    # Display articles
    for idx, row in page_df.iterrows():
        # Create card-like container
        with st.container():
            # Header row
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                st.markdown(f"### {row['title']}")
            
            with col2:
                # Fraud score badge with color coding
                score = row.get('fraud_score', 0)
                if score >= 7:
                    color = "🔴"
                    risk_level = "CRITICAL"
                elif score >= 5:
                    color = "🟠"
                    risk_level = "HIGH"
                elif score >= 3:
                    color = "🟡"
                    risk_level = "MEDIUM"
                else:
                    color = "🟢"
                    risk_level = "LOW"
                
                st.markdown(f"{color} **{risk_level}**")
                st.caption(f"Score: {score:.1f}")
            
            with col3:
                # View details button
                if st.button("View Details", key=f"view_{idx}"):
                    st.session_state.selected_article = row.to_dict()
                    st.session_state.show_modal = True
            
            # Metadata row
            meta_col1, meta_col2, meta_col3 = st.columns(3)
            
            with meta_col1:
                if 'published_at' in row and row['published_at']:
                    st.caption(f"📅 {row['published_at'].strftime('%B %d, %Y')}")
            
            with meta_col2:
                source_map = {
                    'ftc_press': 'FTC Press',
                    'ftc_legal': 'FTC Legal',
                    'ftc_scams': 'FTC Scams'
                }
                source_display = source_map.get(row.get('source', ''), row.get('source', 'Unknown'))
                st.caption(f"📰 {source_display}")
            
            with meta_col3:
                st.caption(f"🏷️ {int(row.get('fraud_hits', 0))} keyword hits")
            
            # Body preview
            body = row.get('body', '')
            preview_length = 250
            preview = body[:preview_length] + "..." if len(body) > preview_length else body
            st.markdown(preview)
            
            # Link
            if 'url' in row and row['url']:
                st.markdown(f"[🔗 Source Article]({row['url']})")
            
            st.markdown("---")
    
    # Pagination controls
    if total_pages > 1:
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])
        
        with col1:
            if st.button("⏮️ First", disabled=(st.session_state.current_page == 0)):
                st.session_state.current_page = 0
                st.rerun()
        
        with col2:
            if st.button("◀️ Previous", disabled=(st.session_state.current_page == 0)):
                st.session_state.current_page -= 1
                st.rerun()
        
        with col3:
            st.markdown(
                f"<div style='text-align: center; padding-top: 8px;'>"
                f"Page {st.session_state.current_page + 1} of {total_pages}"
                f"</div>",
                unsafe_allow_html=True
            )
        
        with col4:
            if st.button("Next ▶️", disabled=(st.session_state.current_page >= total_pages - 1)):
                st.session_state.current_page += 1
                st.rerun()
        
        with col5:
            if st.button("Last ⏭️", disabled=(st.session_state.current_page >= total_pages - 1)):
                st.session_state.current_page = total_pages - 1
                st.rerun()
    
    # Article detail modal
    if st.session_state.get('show_modal', False):
        article = st.session_state.get('selected_article', {})
        
        st.markdown("---")
        st.markdown("## 📄 Article Details")
        
        # Close button
        if st.button("✖️ Close", key="close_modal"):
            st.session_state.show_modal = False
            st.rerun()
        
        # Article details
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {article.get('title', 'N/A')}")
            
            if 'published_at' in article and article['published_at']:
                st.markdown(f"**Published:** {article['published_at']}")
            
            st.markdown(f"**Source:** {article.get('source', 'Unknown')}")
            
            if 'url' in article and article['url']:
                st.markdown(f"**URL:** [{article['url']}]({article['url']})")
        
        with col2:
            st.metric("Fraud Score", f"{article.get('fraud_score', 0):.2f}")
            st.metric("Keyword Hits", int(article.get('fraud_hits', 0)))
            st.metric("Is Fraud", "✅ Yes" if article.get('is_fraud', False) else "❌ No")
        
        st.markdown("---")
        
        st.markdown("### 📝 Full Content")
        st.markdown(article.get('body', 'No content available'))
        
        st.markdown("---")
        
        # Action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔗 Open in Browser"):
                if 'url' in article and article['url']:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={article["url"]}">', unsafe_allow_html=True)
        
        with col2:
            # Export single article
            article_text = f"""
Title: {article.get('title', 'N/A')}
Published: {article.get('published_at', 'N/A')}
Source: {article.get('source', 'N/A')}
Fraud Score: {article.get('fraud_score', 0):.2f}
URL: {article.get('url', 'N/A')}

Content:
{article.get('body', 'N/A')}
            """
            st.download_button(
                label="💾 Download Article",
                data=article_text.encode('utf-8'),
                file_name=f"article_{article.get('title', 'unknown')[:50]}.txt",
                mime="text/plain"
            ) 