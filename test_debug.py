from dashboard.utils.data_loader import DataLoader
from datetime import datetime

loader = DataLoader()

# Test with no filters
print("=== Testing with NO filters ===")
df = loader.load_articles({})
print(f"Total articles loaded: {len(df)}")
if len(df) > 0:
    print(f"Columns: {df.columns.tolist()}")
    print(f"\nSources found: {df['source'].value_counts()}")
    print(f"\nDate range: {df['published_at'].min()} to {df['published_at'].max()}")
    print(f"\nFraud scores: min={df['fraud_score'].min()}, max={df['fraud_score'].max()}, mean={df['fraud_score'].mean():.2f}")

# Test with wide date filter
print("\n=== Testing with WIDE date filter ===")
filters = {
    'date_range': (datetime(2020, 1, 1).date(), datetime(2030, 12, 31).date()),
    'sources': ['All'],
    'min_fraud_score': 0.0
}
df2 = loader.load_articles(filters)
print(f"Total articles with filters: {len(df2)}")
