import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from supabase import create_client
from bertopic import BERTopic
from keybert import KeyBERT
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
from collections import Counter

load_dotenv()


# Custom JSON encoder to handle numpy types
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return super().default(obj)


class SupabaseNLPPipeline:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

        print(f"Connecting to Supabase: {url[:30]}...")
        self.supabase = create_client(url, key)

        print("Initializing NLP models...")
        self.topic_model = BERTopic(min_topic_size=3)
        self.kw_model = KeyBERT()

        print("Loading sentence transformer...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        # Store results locally if database updates fail
        self.results = {
            'topics': {},
            'keywords': {},
            'embeddings': {},
            'articles': []
        }

        print("✅ Initialization complete!\n")

    def fetch_articles(self):
        """Fetch articles from Supabase"""
        print("Fetching articles from database...")
        response = self.supabase.table('press_releases').select('*').execute()
        articles = response.data
        print(f"Fetched {len(articles)} articles\n")
        self.results['articles'] = articles
        return articles

    def run_topic_modeling(self):
        """Run BERTopic modeling on articles"""
        articles = self.fetch_articles()

        if not articles:
            print("⚠️  No articles found for topic modeling")
            return

        # Extract article bodies/summaries
        texts = []
        article_ids = []
        for article in articles:
            text = article.get('body') or article.get('summary') or article.get('title', '')
            if text:
                texts.append(text)
                article_ids.append(article['id'])

        if len(texts) < 3:
            print(f"⚠️  Not enough texts for topic modeling (need at least 3, got {len(texts)})")
            return

        print(f"Running topic modeling on {len(texts)} documents...")
        topics, probabilities = self.topic_model.fit_transform(texts)

        # Get topic info
        topic_info = self.topic_model.get_topic_info()
        print(f"\n✅ Found {len(topic_info)} topics:")
        print(topic_info.head(10))

        # Store results locally
        for article_id, topic_id in zip(article_ids, topics):
            self.results['topics'][article_id] = int(topic_id)

        # Try to update database, but continue if it fails
        print("\nAttempting to save topic assignments to database...")
        success = True
        try:
            for i, article in enumerate(articles):
                if i < len(topics):
                    topic_id = int(topics[i])
                    self.supabase.table('press_releases').update({
                        'topic_id': topic_id
                    }).eq('id', article['id']).execute()
            print("✅ Topic assignments saved to database")
        except Exception as e:
            print(f"⚠️  Could not save to database: {e}")
            print("   Topics stored locally instead - will be saved to JSON/CSV")
            success = False

        print("✅ Topic modeling complete!")
        return topic_info, topics

    def extract_keywords(self):
        """Extract keywords using KeyBERT"""
        articles = self.results.get('articles') or self.fetch_articles()

        if not articles:
            print("⚠️  No articles found for keyword extraction")
            return

        print(f"Extracting keywords from {len(articles)} articles...")

        all_keywords = []
        
        for i, article in enumerate(articles):
            text = article.get('body') or article.get('summary') or article.get('title', '')

            if not text:
                continue

            # Extract top 5 keywords
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),
                stop_words='english',
                top_n=5
            )

            # Store keywords as list of strings
            keyword_list = [kw[0] for kw in keywords]
            all_keywords.extend(keyword_list)
            
            # Store locally
            self.results['keywords'][article['id']] = keyword_list

            # Try to update database
            try:
                self.supabase.table('press_releases').update({
                    'keywords': keyword_list
                }).eq('id', article['id']).execute()
                
                if i == 0:
                    print("✅ Successfully saving keywords to database")
            except Exception as e:
                if i == 0:
                    print(f"⚠️  Could not save keywords to database: {e}")
                    print("   Keywords stored locally instead - will be saved to JSON/CSV")
                break

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(articles)} articles...")

        print("✅ Keyword extraction complete!")
        
        # Calculate top keywords across all articles
        keyword_counts = Counter(all_keywords)
        top_keywords = keyword_counts.most_common(10)
        
        return top_keywords

    def generate_embeddings(self):
        """Generate embeddings for articles"""
        articles = self.results.get('articles') or self.fetch_articles()

        if not articles:
            print("⚠️  No articles found for embedding generation")
            return

        print(f"Generating embeddings for {len(articles)} articles...")

        for i, article in enumerate(articles):
            # Combine title and summary/body for embedding
            title = article.get('title', '')
            body = article.get('body') or article.get('summary', '')
            text = f"{title}. {body[:500]}"  # Limit to first 500 chars of body

            if not text.strip():
                continue

            # Generate embedding
            embedding = self.embedding_model.encode(text)

            # Convert to list for JSON storage
            embedding_list = embedding.tolist()
            
            # Store locally
            self.results['embeddings'][article['id']] = embedding_list

            # Try to update database
            try:
                self.supabase.table('press_releases').update({
                    'embedding': embedding_list
                }).eq('id', article['id']).execute()
                
                if i == 0:
                    print("✅ Successfully saving embeddings to database")
            except Exception as e:
                if i == 0:
                    print(f"⚠️  Could not save embeddings to database: {e}")
                    print("   Embeddings stored locally instead - will be saved to JSON/CSV")
                break

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1}/{len(articles)} articles...")

        print("✅ Embedding generation complete!")

    def analyze_trends(self, top_keywords):
        """Identify top 3 fraud trends based on keywords and topics"""
        print("\n" + "=" * 50)
        print("Analyzing Fraud Trends...")
        print("=" * 50)
        
        # Get topic info
        topic_info = self.topic_model.get_topic_info()
        
        trends = []
        
        # Trend 1: Most common topic
        if len(topic_info) > 1:  # Exclude outlier topic (-1)
            main_topic = topic_info.iloc[1]
            topic_words = main_topic['Representation'][:5]
            trends.append({
                'rank': 1,
                'name': 'Primary Fraud Pattern',
                'keywords': [str(w) for w in topic_words],
                'count': int(main_topic['Count']),
                'description': f"Most common fraud pattern involving: {', '.join(str(w) for w in topic_words)}"
            })
        
        # Trend 2: Top keywords indicate focus areas
        if top_keywords and len(top_keywords) >= 3:
            trend_keywords = [str(kw[0]) for kw in top_keywords[:5]]
            trends.append({
                'rank': 2,
                'name': 'Emerging Fraud Terminology',
                'keywords': trend_keywords,
                'count': int(sum([kw[1] for kw in top_keywords[:5]])),
                'description': f"Key fraud terms appearing frequently: {', '.join(trend_keywords)}"
            })
        
        # Trend 3: Secondary topic if exists
        if len(topic_info) > 2:
            secondary_topic = topic_info.iloc[2]
            topic_words = secondary_topic['Representation'][:5]
            trends.append({
                'rank': 3,
                'name': 'Secondary Fraud Pattern',
                'keywords': [str(w) for w in topic_words],
                'count': int(secondary_topic['Count']),
                'description': f"Additional fraud pattern involving: {', '.join(str(w) for w in topic_words)}"
            })
        
        self.results['trends'] = trends
        
        print("\n🔍 TOP 3 FRAUD TRENDS DETECTED:")
        print("=" * 50)
        for trend in trends:
            print(f"\n{trend['rank']}. {trend['name']}")
            print(f"   Keywords: {', '.join(trend['keywords'])}")
            print(f"   Occurrences: {trend['count']}")
            print(f"   {trend['description']}")
        
        return trends

    def save_results(self):
        """Save all results to JSON and CSV files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save comprehensive JSON
        json_filename = f"fraud_analysis_results_{timestamp}.json"
        with open(json_filename, 'w') as f:
            # Create a serializable version
            serializable_results = {
                'timestamp': timestamp,
                'total_articles': len(self.results['articles']),
                'topics': {str(k): int(v) for k, v in self.results['topics'].items()},
                'keywords': {str(k): v for k, v in self.results['keywords'].items()},
                'trends': [
                    {
                        'rank': t['rank'],
                        'name': t['name'],
                        'keywords': [str(kw) for kw in t['keywords']],
                        'count': int(t['count']),
                        'description': t['description']
                    }
                    for t in self.results.get('trends', [])
                ],
                'summary': {
                    'total_topics': len(set(self.results['topics'].values())) if self.results['topics'] else 0,
                    'articles_analyzed': len(self.results['keywords']),
                }
            }
            json.dump(serializable_results, f, indent=2, cls=NumpyEncoder)
        
        print(f"\n✅ Saved comprehensive results to: {json_filename}")
        
        # Create DataFrame for CSV export
        data = []
        for article in self.results['articles']:
            article_id = article['id']
            data.append({
                'article_id': article_id,
                'title': article.get('title', ''),
                'date': article.get('created_at', ''),
                'topic_id': self.results['topics'].get(article_id, -1),
                'keywords': ', '.join(self.results['keywords'].get(article_id, [])),
                'has_embedding': article_id in self.results['embeddings']
            })
        
        df = pd.DataFrame(data)
        csv_filename = f"fraud_analysis_results_{timestamp}.csv"
        df.to_csv(csv_filename, index=False)
        
        print(f"✅ Saved tabular results to: {csv_filename}")
        
        # Create summary report
        summary_filename = f"fraud_analysis_summary_{timestamp}.txt"
        with open(summary_filename, 'w') as f:
            f.write("=" * 70 + "\n")
            f.write("FRAUD ANALYSIS SUMMARY REPORT\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 70 + "\n\n")
            
            f.write(f"Total Articles Analyzed: {len(self.results['articles'])}\n")
            f.write(f"Total Topics Discovered: {len(set(self.results['topics'].values()))}\n")
            f.write(f"Total Keywords Extracted: {len(self.results['keywords'])}\n\n")
            
            if 'trends' in self.results:
                f.write("=" * 70 + "\n")
                f.write("TOP 3 FRAUD TRENDS\n")
                f.write("=" * 70 + "\n\n")
                for trend in self.results['trends']:
                    f.write(f"{trend['rank']}. {trend['name']}\n")
                    f.write(f"   Keywords: {', '.join(str(k) for k in trend['keywords'])}\n")
                    f.write(f"   Occurrences: {trend['count']}\n")
                    f.write(f"   {trend['description']}\n\n")
        
        print(f"✅ Saved summary report to: {summary_filename}")
        
        return json_filename, csv_filename, summary_filename

    def run_full_pipeline(self):
        """Run all analysis steps"""
        print("\n🚀 Starting NLP Pipeline...\n")

        print("=" * 50)
        print("1. Running topic modeling...")
        print("=" * 50)
        topic_info, topics = self.run_topic_modeling()

        print("\n" + "=" * 50)
        print("2. Extracting keywords...")
        print("=" * 50)
        top_keywords = self.extract_keywords()

        print("\n" + "=" * 50)
        print("3. Generating embeddings...")
        print("=" * 50)
        self.generate_embeddings()

        print("\n" + "=" * 50)
        print("4. Analyzing trends...")
        print("=" * 50)
        trends = self.analyze_trends(top_keywords)

        print("\n" + "=" * 50)
        print("5. Saving results...")
        print("=" * 50)
        files = self.save_results()

        print("\n" + "=" * 70)
        print("✅ ANALYSIS COMPLETE!")
        print("=" * 70)
        print("\n📊 SUMMARY:")
        print(f"   • {len(self.results['articles'])} articles analyzed")
        print(f"   • {len(set(self.results['topics'].values()))} topics discovered")
        print(f"   • {len(top_keywords)} unique keywords extracted")
        print(f"   • 3 fraud trends identified")
        print(f"\n📁 Output files:")
        for f in files:
            print(f"   • {f}")
        print("\n" + "=" * 70)


if __name__ == "__main__":
    pipeline = SupabaseNLPPipeline()
    pipeline.run_full_pipeline()