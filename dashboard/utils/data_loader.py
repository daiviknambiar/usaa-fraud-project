import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import json
from collections import Counter
import re
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.detect.fraud_detector import detect_fraud_for_record
except ImportError:
    detect_fraud_for_record = None

class DataLoader:
    """Handles loading and processing fraud intelligence data"""
    
    def __init__(self):
        # Get project root directory
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        
    def load_articles(self, filters=None):
        """
        Load articles from JSONL files with optional filtering
        
        Args:
            filters (dict): Optional filters containing:
                - date_range: tuple of (start_date, end_date)
                - sources: list of source names
                - min_fraud_score: minimum fraud score threshold
        
        Returns:
            pd.DataFrame: Loaded and filtered articles
        """
        if filters is None:
            filters = {}
        
        # Load all JSONL files from data directory
        articles = []
        
        if not self.data_dir.exists():
            return pd.DataFrame()
        
        # Read all .jsonl files
        for jsonl_file in self.data_dir.glob("*.jsonl"):
            try:
                with open(jsonl_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.strip():
                            article = json.loads(line)
                            
                            # Apply fraud detection if not already present
                            if 'fraud_score' not in article and detect_fraud_for_record:
                                article = detect_fraud_for_record(article)
                            
                            articles.append(article)
            except Exception as e:
                print(f"Error reading {jsonl_file}: {e}")
                continue
        
        if not articles:
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(articles)
        
        # DEBUG
        print(f"\n=== DEBUG DATA_LOADER ===")
        print(f"Total articles loaded from files: {len(df)}")
        
        # Normalize column names and data types
        df = self._normalize_dataframe(df)
        
        # DEBUG
        print(f"After normalization: {len(df)}")
        if len(df) > 0:
            # Check for any remaining string dates
            valid_dates = df['published_at'].notna()
            print(f"Valid dates: {valid_dates.sum()} / {len(df)}")
            if valid_dates.sum() > 0:
                print(f"Date range: {df.loc[valid_dates, 'published_at'].min()} to {df.loc[valid_dates, 'published_at'].max()}")
            print(f"Fraud score range: {df['fraud_score'].min()} to {df['fraud_score'].max()}")
            print(f"Sources: {df['source'].value_counts().to_dict()}")
        
        # Apply filters
        df = self._apply_filters(df, filters)
        
        # DEBUG
        print(f"After filters: {len(df)}")
        print(f"Filters applied: {filters}")
        print("=" * 50)
        
        return df
    
    def _normalize_dataframe(self, df):
        """Normalize the dataframe structure and data types"""
        
        # Ensure required columns exist
        required_cols = ['title', 'url', 'body', 'source']
        for col in required_cols:
            if col not in df.columns:
                df[col] = ''
        
        # DEBUG: Check published column before parsing
        if 'published' in df.columns:
            print(f"DEBUG: Found 'published' column with {df['published'].notna().sum()} non-null values")
        
        # Handle date columns - simple approach
        date_col = None
        if 'published_at' in df.columns:
            date_col = 'published_at'
        elif 'published' in df.columns:
            date_col = 'published'
            # Rename to published_at for consistency
            df['published_at'] = df['published']
        
        if date_col:
            # Ensure column is string type first to handle mixed types
            df['published_at'] = df['published_at'].astype(str)
            
            # Replace 'nan', 'None', etc. with actual NaN
            df['published_at'] = df['published_at'].replace(['nan', 'None', 'NaT', ''], pd.NA)
            
            # Parse dates
            df['published_at'] = pd.to_datetime(df['published_at'], errors='coerce')
            
            print(f"DEBUG: After parsing: {df['published_at'].notna().sum()} valid dates")
            
            # Handle timezone differences
            if df['published_at'].notna().sum() > 0:
                # For any tz-aware dates, convert to naive
                for idx in df[df['published_at'].notna()].index:
                    if df.loc[idx, 'published_at'].tzinfo is not None:
                        df.loc[idx, 'published_at'] = df.loc[idx, 'published_at'].replace(tzinfo=None)
            
            print(f"DEBUG: Final valid dates: {df['published_at'].notna().sum()} out of {len(df)}")
        else:
            df['published_at'] = pd.NaT
        
        # Handle fraud detection columns
        if 'fraud_score' not in df.columns:
            df['fraud_score'] = 0.0
        else:
            df['fraud_score'] = pd.to_numeric(df['fraud_score'], errors='coerce').fillna(0.0)
        
        if 'fraud_hits' not in df.columns:
            df['fraud_hits'] = 0
        else:
            df['fraud_hits'] = pd.to_numeric(df['fraud_hits'], errors='coerce').fillna(0).astype(int)
        
        if 'is_fraud' not in df.columns:
            df['is_fraud'] = df['fraud_score'] >= 2.0
        
        # Normalize source names
        if 'source' in df.columns:
            source_map = {
                'FTC Press Releases': 'ftc_press',
                'FTC Legal Cases': 'ftc_legal',
                'FTC Consumer Scams': 'ftc_scams',
                'FTC DNC Complaints': 'ftc_dnc',
                'press': 'ftc_press',
                'legal': 'ftc_legal',
                'scams': 'ftc_scams',
                'dnc': 'ftc_dnc'
            }
            df['source'] = df['source'].map(lambda x: source_map.get(x, x))
        
        return df
    
    def _apply_filters(self, df, filters):
        """Apply filtering based on user selections"""
        
        if len(df) == 0:
            return df
        
        # SKIP DATE FILTER - just show all articles
        print(f"DEBUG Filter: Skipping date filter, showing all articles")
        
        # Source filter
        if 'sources' in filters and filters['sources']:
            sources = filters['sources']
            if 'All' not in sources:
                # Map display names to internal names
                source_map = {
                    'FTC Press Releases': 'ftc_press',
                    'FTC Legal Cases': 'ftc_legal',
                    'FTC Consumer Scams': 'ftc_scams',
                    'FTC DNC Complaints': 'ftc_dnc'
                }
                internal_sources = [source_map.get(s, s) for s in sources]
                before_filter = len(df)
                df = df[df['source'].isin(internal_sources)]
                print(f"DEBUG Filter: Source filter removed {before_filter - len(df)} articles")
        
        # Fraud score filter
        if 'min_fraud_score' in filters:
            min_score = filters['min_fraud_score']
            before_filter = len(df)
            df = df[df['fraud_score'] >= min_score]
            print(f"DEBUG Filter: Fraud score filter (>={min_score}) removed {before_filter - len(df)} articles")
        
        return df
    
    def get_summary_stats(self, df):
        """Calculate summary statistics for the dashboard"""
        
        if len(df) == 0:
            return {
                'total_articles': 0,
                'high_risk_count': 0,
                'avg_fraud_score': 0.0,
                'sources_count': 0
            }
        
        stats = {
            'total_articles': len(df),
            'high_risk_count': len(df[df['fraud_score'] >= 5.0]),
            'avg_fraud_score': df['fraud_score'].mean(),
            'sources_count': df['source'].nunique() if 'source' in df.columns else 0
        }
        
        return stats
    
    def get_time_series_data(self, df, freq='W'):
        """
        Get time series data for visualizations
        
        Args:
            df: DataFrame with articles
            freq: Pandas frequency string ('D', 'W', 'M')
        
        Returns:
            pd.DataFrame: Time series with date, count, and avg_fraud_score
        """
        
        if len(df) == 0 or 'published_at' not in df.columns:
            return pd.DataFrame()
        
        # Remove rows with invalid dates
        df_valid = df[df['published_at'].notna()].copy()
        
        if len(df_valid) == 0:
            return pd.DataFrame()
        
        # Set published_at as index
        df_valid.set_index('published_at', inplace=True)
        
        # Resample and aggregate
        time_series = df_valid.resample(freq).agg({
            'title': 'count',
            'fraud_score': 'mean'
        }).reset_index()
        
        time_series.columns = ['date', 'count', 'avg_fraud_score']
        
        # Fill NaN fraud scores with 0
        time_series['avg_fraud_score'] = time_series['avg_fraud_score'].fillna(0)
        
        return time_series
    
    def get_top_keywords(self, df, n=20):
        """
        Extract top fraud-related keywords from articles
        
        Args:
            df: DataFrame with articles
            n: Number of top keywords to return
        
        Returns:
            pd.DataFrame: Top keywords with counts
        """
        
        if len(df) == 0:
            return pd.DataFrame()
        
        # Define fraud keywords to look for
        fraud_keywords = [
            'fraud', 'scam', 'phishing', 'identity theft', 'identity-theft',
            'wire transfer', 'ransomware', 'malware', 'ponzi', 'pyramid scheme',
            'money mule', 'business email compromise', 'fake invoice', 
            'refund scam', 'tech support scam', 'romance scam', 
            'cryptocurrency scam', 'investment fraud', 'credit card fraud',
            'debit card', 'social security', 'personal information',
            'unauthorized', 'victim', 'cybercrime', 'hacker', 'breach'
        ]
        
        # Count keyword occurrences
        keyword_counts = Counter()
        
        for _, row in df.iterrows():
            # Convert to string to handle NaN/float values
            title = str(row.get('title', '')) if pd.notna(row.get('title')) else ''
            body = str(row.get('body', '')) if pd.notna(row.get('body')) else ''
            text = (title + ' ' + body).lower()
            
            for keyword in fraud_keywords:
                count = text.count(keyword)
                if count > 0:
                    keyword_counts[keyword] += count
        
        # Convert to DataFrame
        if not keyword_counts:
            return pd.DataFrame()
        
        keywords_df = pd.DataFrame(
            list(keyword_counts.most_common(n)),
            columns=['keyword', 'count']
        )
        
        return keywords_df
    
    def search_articles(self, df, query):
        """
        Search articles by query string
        
        Args:
            df: DataFrame with articles
            query: Search query string
        
        Returns:
            pd.DataFrame: Filtered articles matching query
        """
        
        if len(df) == 0 or not query:
            return df
        
        query_lower = query.lower()
        
        mask = (
            df['title'].str.lower().str.contains(query_lower, na=False) |
            df['body'].str.lower().str.contains(query_lower, na=False)
        )
        
        return df[mask]