import os
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

class DataLoader:
    """Handles all data loading operations from Supabase and local files"""
    
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
        self.client = None
        
        if self.supabase_url and self.supabase_key:
            try:
                self.client = create_client(self.supabase_url, self.supabase_key)
            except Exception as e:
                st.warning(f"Could not connect to Supabase: {e}")
    
    def load_articles(self, filters=None):
        """
        Load fraud articles from Supabase with optional filters
        
        Args:
            filters: dict with keys 'date_range', 'sources', 'min_fraud_score'
        
        Returns:
            pandas DataFrame
        """
        if not self.client:
            # Fallback to local data if Supabase not available
            return self._load_local_data(filters)
        
        try:
            # Base query
            query = self.client.table('fraud_articles').select('*')
            
            # Apply filters if provided
            if filters:
                # Fraud score filter
                if 'min_fraud_score' in filters:
                    query = query.gte('fraud_score', filters['min_fraud_score'])
                
                # Date range filter
                if 'date_range' in filters and len(filters['date_range']) == 2:
                    start_date, end_date = filters['date_range']
                    query = query.gte('published_at', start_date.isoformat())
                    query = query.lte('published_at', end_date.isoformat())
            
            # Execute query
            response = query.execute()
            
            # Convert to DataFrame
            df = pd.DataFrame(response.data)
            
            if len(df) > 0:
                # Convert date column
                if 'published_at' in df.columns:
                    df['published_at'] = pd.to_datetime(df['published_at'])
                
                # Apply source filter (post-query since it's more complex)
                if filters and 'sources' in filters and 'All' not in filters['sources']:
                    source_map = {
                        'FTC Press Releases': 'ftc_press',
                        'FTC Legal Cases': 'ftc_legal',
                        'FTC Consumer Scams': 'ftc_scams'
                    }
                    valid_sources = [source_map.get(s, s) for s in filters['sources']]
                    df = df[df['source'].isin(valid_sources)]
            
            return df
            
        except Exception as e:
            st.error(f"Error loading data from Supabase: {e}")
            return self._load_local_data(filters)
    
    def _load_local_data(self, filters=None):
        """
        Fallback: Load data from local JSONL files
        """
        import json
        from pathlib import Path
        
        data_dir = Path(__file__).parent.parent.parent / 'data'
        all_records = []
        
        if data_dir.exists():
            for jsonl_file in data_dir.glob('*.jsonl'):
                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if line.strip():
                                record = json.loads(line)
                                all_records.append(record)
                except Exception as e:
                    st.warning(f"Could not read {jsonl_file.name}: {e}")
        
        if not all_records:
            # Return empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'title', 'url', 'published_at', 'body', 'source', 
                'fraud_score', 'fraud_hits', 'is_fraud'
            ])
        
        df = pd.DataFrame(all_records)
        
        # Standardize column names
        if 'published' in df.columns and 'published_at' not in df.columns:
            df['published_at'] = df['published']
        
        if 'published_at' in df.columns:
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
        
        # Apply fraud detection if not already done
        if 'fraud_score' not in df.columns:
            from src.detect.fraud_detector import FraudDetector
            detector = FraudDetector()
            
            for idx, row in df.iterrows():
                result = detector.detect(row.get('body', ''))
                df.at[idx, 'fraud_score'] = result['fraud_score']
                df.at[idx, 'fraud_hits'] = result['fraud_hits']
                df.at[idx, 'is_fraud'] = result['is_fraud']
        
        # Apply filters
        if filters:
            if 'min_fraud_score' in filters:
                df = df[df['fraud_score'] >= filters['min_fraud_score']]
            
            if 'date_range' in filters and len(filters['date_range']) == 2:
                start_date, end_date = filters['date_range']
                df = df[
                    (df['published_at'] >= pd.Timestamp(start_date)) &
                    (df['published_at'] <= pd.Timestamp(end_date))
                ]
            
            if 'sources' in filters and 'All' not in filters['sources']:
                source_map = {
                    'FTC Press Releases': 'ftc_press',
                    'FTC Legal Cases': 'ftc_legal',
                    'FTC Consumer Scams': 'ftc_scams'
                }
                valid_sources = [source_map.get(s, s) for s in filters['sources']]
                df = df[df['source'].isin(valid_sources)]
        
        return df
    
    def get_summary_stats(self, df):
        """Calculate summary statistics from the dataframe"""
        stats = {
            'total_articles': len(df),
            'avg_fraud_score': df['fraud_score'].mean() if len(df) > 0 else 0,
            'high_risk_count': len(df[df['fraud_score'] >= 5]) if len(df) > 0 else 0,
            'sources_count': df['source'].nunique() if len(df) > 0 else 0,
        }
        
        # Date range
        if len(df) > 0 and 'published_at' in df.columns:
            stats['date_range'] = (
                df['published_at'].min(),
                df['published_at'].max()
            )
        else:
            stats['date_range'] = (None, None)
        
        return stats
    
    def get_time_series_data(self, df, freq='D'):
        """
        Aggregate data by time period
        
        Args:
            df: DataFrame with articles
            freq: 'D' for daily, 'W' for weekly, 'M' for monthly
        
        Returns:
            DataFrame with time series data
        """
        if len(df) == 0 or 'published_at' not in df.columns:
            return pd.DataFrame()
        
        df_copy = df.copy()
        df_copy['date'] = pd.to_datetime(df_copy['published_at'])
        df_copy = df_copy.set_index('date')
        
        # Resample by frequency
        time_series = df_copy.resample(freq).agg({
            'title': 'count',
            'fraud_score': 'mean'
        }).rename(columns={'title': 'count', 'fraud_score': 'avg_fraud_score'})
        
        time_series = time_series.reset_index()
        return time_series
    
    def get_top_keywords(self, df, n=20):
        """Extract most common keywords from articles"""
        if len(df) == 0:
            return pd.DataFrame()
        
        from collections import Counter
        import re
        
        # Combine all text
        all_text = ' '.join(df['body'].fillna('').astype(str))
        
        # Simple tokenization
        words = re.findall(r'\b[a-z]{3,}\b', all_text.lower())
        
        # Remove common stop words
        stop_words = {'the', 'and', 'for', 'are', 'with', 'that', 'this', 'from', 'have', 'was', 'were', 'been'}
        words = [w for w in words if w not in stop_words]
        
        # Count
        word_counts = Counter(words).most_common(n)
        
        return pd.DataFrame(word_counts, columns=['keyword', 'count'])