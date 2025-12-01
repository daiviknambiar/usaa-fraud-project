import streamlit as st
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.detect.fraud_detector import FraudDetector

def render(loader):
    """Render the upload and analyze page"""
    
    st.markdown('<div class="main-header">📤 Upload & Analyze</div>', unsafe_allow_html=True)
    st.markdown("Upload text or documents for immediate fraud detection analysis")
    
    st.markdown("---")
    
    # Analysis mode selector
    col1, col2 = st.columns([1, 3])
    
    with col1:
        analysis_mode = st.radio(
            "Analysis Mode",
            ["Text Input", "File Upload"],
            label_visibility="collapsed"
        )
    
    st.markdown("---")
    
    # Initialize fraud detector
    detector = FraudDetector()
    
    if analysis_mode == "Text Input":
        render_text_analysis(detector)
    else:
        render_file_upload(detector)

def render_text_analysis(detector):
    """Render text input analysis"""
    
    st.subheader("✍️ Text Analysis")
    
    st.markdown("""
    Paste any text content (emails, articles, messages, etc.) to analyze for fraud indicators.
    This uses the same keyword-based detection system as the scrapers.
    """)
    
    # Text input
    text_input = st.text_area(
        "Enter text to analyze",
        height=250,
        placeholder="Paste your text here...",
        label_visibility="collapsed"
    )
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        analyze_button = st.button("🔍 Analyze Text", type="primary", use_container_width=True)
    
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
        if clear_button:
            st.rerun()
    
    if analyze_button and text_input:
        with st.spinner("Analyzing..."):
            result = detector.detect(text_input)
            
            st.markdown("---")
            st.subheader("📊 Analysis Results")
            
            # Results metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                fraud_status = "🔴 FRAUD DETECTED" if result['is_fraud'] else "🟢 NO FRAUD"
                st.markdown(f"### {fraud_status}")
            
            with col2:
                st.metric("Fraud Score", f"{result['fraud_score']:.1f}")
            
            with col3:
                st.metric("Keyword Hits", result['fraud_hits'])
            
            with col4:
                risk_level = get_risk_level(result['fraud_score'])
                st.metric("Risk Level", risk_level)
            
            # Detailed breakdown
            st.markdown("---")
            st.markdown("### 🔍 Detailed Breakdown")
            
            if result['fraud_hits'] > 0:
                st.markdown("#### Fraud Keywords Found:")
                
                # Find which keywords were detected
                detected_keywords = []
                text_lower = text_input.lower()
                
                # Get keywords from detector
                keywords = detector.fraud_keywords if hasattr(detector, 'fraud_keywords') else [
                    'fraud', 'scam', 'phishing', 'identity theft', 'wire transfer',
                    'ransomware', 'malware', 'ponzi', 'pyramid scheme', 'money mule',
                    'business email compromise', 'fake invoice', 'refund scam',
                    'tech support scam', 'romance scam', 'cryptocurrency scam'
                ]
                
                for keyword in keywords:
                    if keyword in text_lower:
                        count = text_lower.count(keyword)
                        detected_keywords.append((keyword, count))
                
                if detected_keywords:
                    keyword_df = {
                        'Keyword': [kw for kw, _ in detected_keywords],
                        'Occurrences': [count for _, count in detected_keywords]
                    }
                    st.dataframe(keyword_df, use_container_width=True)
                else:
                    st.info("Keywords detected but not in the standard list")
                
                # Highlight text
                st.markdown("---")
                st.markdown("#### 📝 Text Preview with Highlights")
                
                highlighted_text = text_input
                for keyword, _ in detected_keywords:
                    # Simple highlighting (case-insensitive)
                    import re
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    highlighted_text = pattern.sub(
                        f'<mark style="background-color: #ffeb3b;">{keyword}</mark>',
                        highlighted_text
                    )
                
                st.markdown(
                    f'<div style="padding: 1rem; background-color: #f5f5f5; border-radius: 0.5rem; max-height: 400px; overflow-y: auto;">{highlighted_text}</div>',
                    unsafe_allow_html=True
                )
            else:
                st.success("✅ No fraud keywords detected in the text")
            
            # Recommendations
            st.markdown("---")
            st.markdown("### 💡 Recommendations")
            
            if result['is_fraud']:
                st.warning("""
                **⚠️ This text shows indicators of potential fraud:**
                - Review the highlighted keywords carefully
                - Verify the source of this content
                - Do not respond to requests for money or personal information
                - Report suspicious content to appropriate authorities
                """)
            else:
                st.info("""
                **ℹ️ No strong fraud indicators detected:**
                - However, always exercise caution with unsolicited messages
                - Verify sender identity through official channels
                - Be wary of urgent requests for money or information
                """)
    
    elif analyze_button:
        st.warning("⚠️ Please enter some text to analyze")

def render_file_upload(detector):
    """Render file upload analysis"""
    
    st.subheader("📁 File Upload Analysis")
    
    st.markdown("""
    Upload a text file (.txt) or document to analyze for fraud indicators.
    Support for additional formats (PDF, DOCX) coming soon.
    """)
    
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['txt'],
        label_visibility="collapsed"
    )
    
    if uploaded_file is not None:
        # Read file
        try:
            text_content = uploaded_file.read().decode('utf-8')
            
            st.success(f"✅ File uploaded: {uploaded_file.name} ({len(text_content)} characters)")
            
            # Show preview
            with st.expander("📄 File Preview"):
                st.text(text_content[:500] + "..." if len(text_content) > 500 else text_content)
            
            if st.button("🔍 Analyze File", type="primary"):
                with st.spinner("Analyzing..."):
                    result = detector.detect(text_content)
                    
                    st.markdown("---")
                    st.subheader("📊 Analysis Results")
                    
                    # Results metrics
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        fraud_status = "🔴 FRAUD" if result['is_fraud'] else "🟢 CLEAN"
                        st.markdown(f"### {fraud_status}")
                    
                    with col2:
                        st.metric("Fraud Score", f"{result['fraud_score']:.1f}")
                    
                    with col3:
                        st.metric("Keyword Hits", result['fraud_hits'])
                    
                    # Risk assessment
                    st.markdown("---")
                    risk_level = get_risk_level(result['fraud_score'])
                    
                    if result['is_fraud']:
                        st.error(f"⚠️ **Risk Level: {risk_level}**")
                        st.markdown("""
                        This file contains multiple fraud indicators. Exercise extreme caution.
                        """)
                    else:
                        st.success("✅ No significant fraud indicators detected")
                    
                    # Export results
                    st.markdown("---")
                    st.markdown("### 💾 Export Results")
                    
                    report = f"""
FRAUD DETECTION ANALYSIS REPORT
================================

File: {uploaded_file.name}
Analyzed: {st.session_state.get('analysis_time', 'N/A')}

RESULTS:
--------
Fraud Detected: {'YES' if result['is_fraud'] else 'NO'}
Fraud Score: {result['fraud_score']:.2f}
Keyword Hits: {result['fraud_hits']}
Risk Level: {risk_level}

CONTENT PREVIEW:
----------------
{text_content[:1000]}...

---
Generated by USAA Fraud Intelligence Dashboard
                    """
                    
                    st.download_button(
                        label="📥 Download Report",
                        data=report,
                        file_name=f"fraud_analysis_{uploaded_file.name}.txt",
                        mime="text/plain"
                    )
        
        except Exception as e:
            st.error(f"❌ Error reading file: {e}")
    
    st.markdown("---")
    st.info("""
    **Tip:** For best results, upload complete documents or emails. 
    Short text snippets may not provide enough context for accurate analysis.
    """)

def get_risk_level(fraud_score):
    """Get risk level based on fraud score"""
    if fraud_score >= 7:
        return "CRITICAL"
    elif fraud_score >= 5:
        return "HIGH"
    elif fraud_score >= 3:
        return "MEDIUM"
    else:
        return "LOW"