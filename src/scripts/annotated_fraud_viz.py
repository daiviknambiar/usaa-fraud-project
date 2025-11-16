"""
Create an annotated version of the fraud embeddings visualization
with cluster labels and key insights
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
import json


class SimpleKMeans:
    """Simple K-means implementation"""
    def __init__(self, n_clusters=8, max_iter=100, random_state=42):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        np.random.seed(random_state)
        
    def fit_predict(self, X):
        n_samples = X.shape[0]
        
        # Initialize centroids randomly
        indices = np.random.choice(n_samples, self.n_clusters, replace=False)
        self.centroids = X[indices].copy()
        
        for _ in range(self.max_iter):
            # Assign to nearest centroid
            distances = np.sqrt(((X[:, np.newaxis] - self.centroids) ** 2).sum(axis=2))
            labels = np.argmin(distances, axis=1)
            
            # Update centroids
            new_centroids = np.array([X[labels == k].mean(axis=0) 
                                     for k in range(self.n_clusters)])
            
            # Check convergence
            if np.allclose(self.centroids, new_centroids):
                break
            
            self.centroids = new_centroids
        
        return labels


def load_data():
    """Load embeddings and article data"""
    # Load embeddings
    data = np.load('visualizations/embeddings.npz', allow_pickle=True)
    embeddings = data['embeddings']
    titles = data['titles']
    sources = data['sources']
    
    # Load original articles to get subjects/keywords
    articles_data = []
    data_dir = Path('data')
    for jsonl_file in data_dir.glob('*.jsonl'):
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    articles_data.append(json.loads(line))
    
    return embeddings, titles, sources, articles_data


def reduce_dimensions(embeddings):
    """Simple PCA reduction"""
    mean = np.mean(embeddings, axis=0)
    centered = embeddings - mean
    cov = np.cov(centered.T)
    eigenvalues, eigenvectors = np.linalg.eig(cov)
    idx = eigenvalues.argsort()[::-1]
    components = eigenvectors[:, idx][:, :2]
    reduced = centered @ components
    return reduced.real


def identify_clusters(embeddings, n_clusters=8):
    """Identify major clusters"""
    kmeans = SimpleKMeans(n_clusters=n_clusters, random_state=42)
    labels = kmeans.fit_predict(embeddings)
    centroids = kmeans.centroids
    return labels, centroids


def get_cluster_keywords(cluster_indices, titles, articles_data):
    """Extract common keywords/subjects from a cluster"""
    cluster_titles = [titles[i].lower() for i in cluster_indices]
    cluster_articles = [articles_data[i] for i in cluster_indices if i < len(articles_data)]
    
    # Extract subjects and common words
    keywords = []
    for article in cluster_articles[:200]:  # Sample for performance
        subject = article.get('metadata', {}).get('subject', '')
        if subject and subject != 'Unknown':
            keywords.append(subject.lower())
        
        # Check title for key fraud terms
        title = article.get('title', '').lower()
        body = article.get('body', '').lower()[:500]  # First 500 chars
        text = title + ' ' + body
        
        fraud_patterns = {
            'Robocalls': ['robocall', 'robo call', 'automated call', 'recorded message'],
            'Telemarketing': ['telemarket', 'sales call', 'unsolicited'],
            'Debt Collection': ['debt', 'collection', 'collector', 'owe'],
            'Impersonation': ['impersonat', 'pretend', 'posing as', 'claimed to be'],
            'Tech Support': ['tech support', 'computer', 'virus', 'microsoft', 'apple'],
            'IRS/Tax Scams': ['irs', 'tax', 'revenue', 'refund'],
            'Medicare/Health': ['medicare', 'health insurance', 'medical'],
            'Warranty Scams': ['warranty', 'extended warranty', 'car warranty', 'auto'],
            'Prize/Lottery': ['prize', 'lottery', 'winner', 'sweepstakes', 'won'],
            'Investment': ['investment', 'crypto', 'bitcoin', 'stock', 'trading'],
            'Identity Theft': ['identity', 'ssn', 'social security', 'credit card'],
            'Utility/Energy': ['utility', 'electric', 'power', 'solar', 'energy']
        }
        
        for fraud_type, terms in fraud_patterns.items():
            if any(term in text for term in terms):
                keywords.append(fraud_type)
    
    # Get most common
    if keywords:
        counter = Counter(keywords)
        top_keywords = counter.most_common(2)
        return ' / '.join([kw[0].title() for kw in top_keywords])
    return 'Mixed Topics'


def create_annotated_visualization():
    """Create annotated visualization with cluster labels"""
    print("Loading data...")
    embeddings, titles, sources, articles_data = load_data()
    
    print("Reducing dimensions...")
    coords_2d = reduce_dimensions(embeddings)
    
    print("Identifying clusters...")
    labels, centroids = identify_clusters(embeddings, n_clusters=8)
    centroids_2d = reduce_dimensions(centroids)
    
    # Create figure
    fig, ax = plt.subplots(figsize=(20, 16))
    
    # Color by source
    unique_sources = list(set(sources))
    colors = plt.cm.tab10(np.linspace(0, 1, len(unique_sources)))
    source_to_color = {source: colors[i] for i, source in enumerate(unique_sources)}
    
    # Plot points
    for source in unique_sources:
        mask = [s == source for s in sources]
        count = sum(mask)
        ax.scatter(coords_2d[mask, 0], coords_2d[mask, 1], 
                   label=f'{source} ({count})', alpha=0.5, s=60, 
                   c=[source_to_color[source]], edgecolors='white', linewidth=0.3)
    
    # Annotate clusters
    cluster_colors = plt.cm.Set3(np.linspace(0, 1, 8))
    
    for cluster_id in range(8):
        cluster_mask = labels == cluster_id
        cluster_indices = np.where(cluster_mask)[0]
        
        if len(cluster_indices) < 10:  # Skip tiny clusters
            continue
        
        # Get cluster center in 2D space
        cluster_coords = coords_2d[cluster_mask]
        center_x = np.mean(cluster_coords[:, 0])
        center_y = np.mean(cluster_coords[:, 1])
        
        # Get descriptive label
        cluster_label = get_cluster_keywords(cluster_indices, titles, articles_data)
        cluster_size = len(cluster_indices)
        
        # Draw circle around cluster
        from matplotlib.patches import Circle
        radius = np.std(cluster_coords) * 1.5
        circle = Circle((center_x, center_y), radius, color=cluster_colors[cluster_id], 
                       alpha=0.15, linewidth=2, linestyle='--', fill=True)
        ax.add_patch(circle)
        
        # Add label
        label_text = f"Cluster {cluster_id + 1}\n{cluster_label}\n({cluster_size} articles)"
        ax.annotate(label_text, xy=(center_x, center_y), 
                   fontsize=11, fontweight='bold',
                   bbox=dict(boxstyle='round,pad=0.5', facecolor=cluster_colors[cluster_id], 
                            alpha=0.8, edgecolor='black', linewidth=1.5),
                   ha='center', va='center')
    
    # Title and labels
    plt.suptitle('Annotated Fraud Pattern Analysis', fontsize=22, fontweight='bold', y=0.98)
    ax.set_title(
        'Major fraud types automatically detected through content similarity\n'
        'Each cluster represents a distinct fraud pattern or scam type',
        fontsize=14, pad=20, style='italic'
    )
    
    ax.set_xlabel('Fraud Topic Dimension 1 →', fontsize=14, fontweight='bold')
    ax.set_ylabel('Fraud Topic Dimension 2 →', fontsize=14, fontweight='bold')
    
    # Legend
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=12,
              title='Data Sources', title_fontsize=14, framealpha=0.95,
              edgecolor='black', fancybox=True, shadow=True)
    
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.set_facecolor('#f8f9fa')
    
    # Interpretation guide
    textstr = ('📊 How to Read This Map:\n'
              '1. Each DOT = one fraud case/complaint\n'
              '2. CIRCLES = automatically detected fraud clusters\n'
              '3. CLOSER DOTS = more similar fraud tactics\n'
              '4. CLUSTER LABELS = most common fraud types\n'
              '5. MIXED COLORS = multiple sources confirm pattern')
    
    props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.9, edgecolor='black', linewidth=2)
    ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=11,
           verticalalignment='top', bbox=props, family='monospace')
    
    plt.tight_layout()
    
    # Save
    output_path = Path('visualizations/annotated_fraud_map.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n✅ Annotated visualization saved to {output_path}")
    plt.close()
    
    # Print cluster summary
    print("\n" + "="*80)
    print("FRAUD CLUSTER SUMMARY")
    print("="*80)
    for cluster_id in range(8):
        cluster_mask = labels == cluster_id
        cluster_indices = np.where(cluster_mask)[0]
        cluster_label = get_cluster_keywords(cluster_indices, titles, articles_data)
        cluster_size = len(cluster_indices)
        
        # Get source distribution
        cluster_sources = [sources[i] for i in cluster_indices]
        source_dist = Counter(cluster_sources)
        
        print(f"\nCluster {cluster_id + 1}: {cluster_label}")
        print(f"  Size: {cluster_size} articles ({cluster_size/len(labels)*100:.1f}%)")
        print(f"  Sources: {dict(source_dist)}")
    print("="*80)


if __name__ == "__main__":
    create_annotated_visualization()