"""
Embedding Visualizer for USAA Fraud Project
Generates embeddings from fraud articles and creates 2D/3D visualizations
Uses transformers directly - no scikit-learn or sentence-transformers needed!
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from transformers import AutoTokenizer, AutoModel
import torch
from typing import List, Dict, Tuple
import argparse


def mean_pooling(model_output, attention_mask):
    """Mean pooling to get sentence embeddings"""
    token_embeddings = model_output[0]
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


class SimplePCA:
    """Simple PCA implementation without scikit-learn"""
    def __init__(self, n_components=2):
        self.n_components = n_components
        self.mean = None
        self.components = None
    
    def fit_transform(self, X):
        # Center the data
        self.mean = np.mean(X, axis=0)
        X_centered = X - self.mean
        
        # Compute covariance matrix
        cov = np.cov(X_centered.T)
        
        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eig(cov)
        
        # Sort by eigenvalues
        idx = eigenvalues.argsort()[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]
        
        # Store principal components
        self.components = eigenvectors[:, :self.n_components]
        
        # Transform data
        X_transformed = X_centered @ self.components
        return X_transformed.real


class SimpleTSNE:
    """Simple t-SNE implementation without scikit-learn"""
    def __init__(self, n_components=2, perplexity=30, n_iter=1000, random_state=42):
        self.n_components = n_components
        self.perplexity = perplexity
        self.n_iter = n_iter
        self.random_state = random_state
        np.random.seed(random_state)
    
    def fit_transform(self, X):
        n_samples = X.shape[0]
        
        # Initialize with PCA
        pca = SimplePCA(n_components=self.n_components)
        Y = pca.fit_transform(X)
        Y = Y * 0.0001  # Small initial values
        
        # Compute pairwise distances
        sum_X = np.sum(X**2, axis=1)
        D = sum_X[:, np.newaxis] + sum_X[np.newaxis, :] - 2 * X @ X.T
        D = np.maximum(D, 0)
        
        # Compute P matrix (affinities in high-dimensional space)
        P = self._compute_joint_probabilities(D)
        
        # Gradient descent
        lr = 200.0
        momentum = 0.5
        Y_prev = np.zeros_like(Y)
        
        for i in range(self.n_iter):
            # Compute Q matrix (affinities in low-dimensional space)
            sum_Y = np.sum(Y**2, axis=1)
            num = 1 / (1 + sum_Y[:, np.newaxis] + sum_Y[np.newaxis, :] - 2 * Y @ Y.T)
            np.fill_diagonal(num, 0)
            Q = num / np.sum(num)
            Q = np.maximum(Q, 1e-12)
            
            # Compute gradient
            PQ = P - Q
            grad = np.zeros_like(Y)
            for j in range(n_samples):
                grad[j] = 4 * np.sum((PQ[j] * num[j])[:, np.newaxis] * (Y[j] - Y), axis=0)
            
            # Update with momentum
            Y_update = momentum * Y_prev - lr * grad
            Y = Y + Y_update
            Y_prev = Y_update
            
            # Switch to higher momentum after 250 iterations
            if i == 250:
                momentum = 0.8
            
            # Progress update
            if (i + 1) % 100 == 0:
                print(f"  t-SNE iteration {i+1}/{self.n_iter}")
        
        return Y
    
    def _compute_joint_probabilities(self, D):
        n_samples = D.shape[0]
        P = np.zeros((n_samples, n_samples))
        beta = np.ones(n_samples)
        
        # Compute conditional probabilities
        for i in range(n_samples):
            beta_min, beta_max = -np.inf, np.inf
            Di = D[i, np.concatenate((np.arange(i), np.arange(i+1, n_samples)))]
            
            # Binary search for beta (precision parameter)
            for _ in range(50):
                exp_D = np.exp(-Di * beta[i])
                sum_exp = np.sum(exp_D)
                H = np.log(sum_exp) + beta[i] * np.sum(Di * exp_D) / sum_exp
                
                Hdiff = H - np.log(self.perplexity)
                if abs(Hdiff) < 1e-5:
                    break
                
                if Hdiff > 0:
                    beta_min = beta[i]
                    if beta_max == np.inf:
                        beta[i] *= 2
                    else:
                        beta[i] = (beta[i] + beta_max) / 2
                else:
                    beta_max = beta[i]
                    if beta_min == -np.inf:
                        beta[i] /= 2
                    else:
                        beta[i] = (beta[i] + beta_min) / 2
            
            P[i, np.concatenate((np.arange(i), np.arange(i+1, n_samples)))] = exp_D / sum_exp
        
        # Symmetrize
        P = (P + P.T) / (2 * n_samples)
        return np.maximum(P, 1e-12)


class EmbeddingVisualizer:
    def __init__(self, data_dir: str = "data", output_dir: str = "visualizations"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load model and tokenizer
        print("Loading embedding model (all-MiniLM-L6-v2)...")
        model_name = 'sentence-transformers/all-MiniLM-L6-v2'
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model.to(self.device)
        self.model.eval()
        print(f"Model loaded successfully on {self.device}!")
        
    def load_jsonl_data(self) -> List[Dict]:
        """Load all JSONL files from data directory"""
        articles = []
        
        if not self.data_dir.exists():
            print(f"Warning: {self.data_dir} directory not found")
            return articles
            
        for jsonl_file in self.data_dir.glob("*.jsonl"):
            print(f"Loading {jsonl_file.name}...")
            with open(jsonl_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        article = json.loads(line)
                        articles.append(article)
        
        print(f"Loaded {len(articles)} articles")
        return articles
    
    def generate_embeddings(self, articles: List[Dict]) -> Tuple[np.ndarray, List[str], List[str]]:
        """Generate embeddings for article bodies"""
        texts = []
        titles = []
        sources = []
        
        for article in articles:
            # Combine title and body for better embeddings
            text = f"{article.get('title', '')} {article.get('body', '')}"
            texts.append(text[:1000])  # Limit to 1000 chars for efficiency
            titles.append(article.get('title', 'Untitled'))
            sources.append(article.get('source', 'Unknown'))
        
        print(f"Generating embeddings for {len(texts)} articles...")
        
        # Process in batches
        batch_size = 32
        all_embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            
            # Tokenize
            encoded_input = self.tokenizer(
                batch_texts, 
                padding=True, 
                truncation=True, 
                max_length=512,
                return_tensors='pt'
            ).to(self.device)
            
            # Generate embeddings
            with torch.no_grad():
                model_output = self.model(**encoded_input)
            
            # Mean pooling
            embeddings = mean_pooling(model_output, encoded_input['attention_mask'])
            
            # Normalize embeddings
            embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            all_embeddings.append(embeddings.cpu().numpy())
            
            if (i + batch_size) % 100 == 0:
                print(f"  Processed {min(i + batch_size, len(texts))}/{len(texts)} articles")
        
        embeddings = np.vstack(all_embeddings)
        print(f"Generated embeddings with shape: {embeddings.shape}")
        
        return embeddings, titles, sources
    
    def reduce_dimensions(self, embeddings: np.ndarray, method: str = 'pca', n_components: int = 2) -> np.ndarray:
        """Reduce embeddings to 2D or 3D using PCA or t-SNE"""
        print(f"Reducing dimensions using {method.upper()}...")
        
        if method == 'pca':
            reducer = SimplePCA(n_components=n_components)
        elif method == 'tsne':
            reducer = SimpleTSNE(n_components=n_components, perplexity=min(30, len(embeddings)-1))
        else:
            raise ValueError(f"Unknown method: {method}. Use 'pca' or 'tsne'")
        
        reduced = reducer.fit_transform(embeddings)
        return reduced
    
    def visualize_2d(self, coords: np.ndarray, titles: List[str], sources: List[str], 
                     method: str, filename: str = None):
        """Create 2D scatter plot"""
        plt.figure(figsize=(16, 12))
        
        # Color by source
        unique_sources = list(set(sources))
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_sources)))
        source_to_color = {source: colors[i] for i, source in enumerate(unique_sources)}
        
        for source in unique_sources:
            mask = [s == source for s in sources]
            plt.scatter(coords[mask, 0], coords[mask, 1], 
                       label=source, alpha=0.6, s=50, 
                       c=[source_to_color[source]])
        
        plt.title(f'Fraud Article Embeddings - {method.upper()} Projection', fontsize=16, pad=20)
        plt.xlabel(f'{method.upper()} Component 1', fontsize=12)
        plt.ylabel(f'{method.upper()} Component 2', fontsize=12)
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        if filename is None:
            filename = f'embeddings_2d_{method}.png'
        
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Saved 2D visualization to {filepath}")
        plt.close()
    
    def visualize_3d(self, coords: np.ndarray, titles: List[str], sources: List[str], 
                     method: str, filename: str = None):
        """Create 3D scatter plot"""
        fig = plt.figure(figsize=(16, 12))
        ax = fig.add_subplot(111, projection='3d')
        
        # Color by source
        unique_sources = list(set(sources))
        colors = plt.cm.tab10(np.linspace(0, 1, len(unique_sources)))
        source_to_color = {source: colors[i] for i, source in enumerate(unique_sources)}
        
        for source in unique_sources:
            mask = [s == source for s in sources]
            ax.scatter(coords[mask, 0], coords[mask, 1], coords[mask, 2],
                      label=source, alpha=0.6, s=50,
                      c=[source_to_color[source]])
        
        ax.set_title(f'Fraud Article Embeddings - {method.upper()} Projection (3D)', 
                     fontsize=16, pad=20)
        ax.set_xlabel(f'{method.upper()} Component 1', fontsize=12)
        ax.set_ylabel(f'{method.upper()} Component 2', fontsize=12)
        ax.set_zlabel(f'{method.upper()} Component 3', fontsize=12)
        ax.legend(bbox_to_anchor=(1.15, 1), loc='upper left', fontsize=10)
        
        if filename is None:
            filename = f'embeddings_3d_{method}.png'
        
        filepath = self.output_dir / filename
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Saved 3D visualization to {filepath}")
        plt.close()
    
    def save_embeddings(self, embeddings: np.ndarray, titles: List[str], 
                       sources: List[str], filename: str = "embeddings.npz"):
        """Save embeddings to disk for later use"""
        filepath = self.output_dir / filename
        np.savez(filepath, embeddings=embeddings, titles=titles, sources=sources)
        print(f"Saved embeddings to {filepath}")
    
    def run_full_pipeline(self, methods: List[str] = ['pca', 'tsne'], 
                         dimensions: List[int] = [2, 3]):
        """Run complete visualization pipeline"""
        # Load data
        articles = self.load_jsonl_data()
        if not articles:
            print("No articles found. Make sure JSONL files exist in the data/ directory.")
            return
        
        # Generate embeddings
        embeddings, titles, sources = self.generate_embeddings(articles)
        
        # Save raw embeddings
        self.save_embeddings(embeddings, titles, sources)
        
        # Create visualizations for each method and dimension
        for method in methods:
            for dim in dimensions:
                print(f"\n--- Creating {dim}D visualization with {method.upper()} ---")
                reduced = self.reduce_dimensions(embeddings, method=method, n_components=dim)
                
                if dim == 2:
                    self.visualize_2d(reduced, titles, sources, method)
                elif dim == 3:
                    self.visualize_3d(reduced, titles, sources, method)
        
        print("\n✅ All visualizations complete!")
        print(f"📁 Check the '{self.output_dir}' directory for results")


def main():
    parser = argparse.ArgumentParser(description='Generate embedding visualizations for fraud articles')
    parser.add_argument('--data-dir', default='data', help='Directory containing JSONL files')
    parser.add_argument('--output-dir', default='visualizations', help='Output directory for visualizations')
    parser.add_argument('--methods', nargs='+', default=['pca', 'tsne'], 
                       choices=['pca', 'tsne'],
                       help='Dimensionality reduction methods to use')
    parser.add_argument('--dims', nargs='+', type=int, default=[2, 3],
                       choices=[2, 3],
                       help='Dimensions for visualization (2 or 3)')
    
    args = parser.parse_args()
    
    visualizer = EmbeddingVisualizer(data_dir=args.data_dir, output_dir=args.output_dir)
    visualizer.run_full_pipeline(methods=args.methods, dimensions=args.dims)


if __name__ == "__main__":
    main()