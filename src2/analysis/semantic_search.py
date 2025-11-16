import os
from supabase import create_client
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

load_dotenv()


class SemanticSearcher:
    def __init__(self):
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")

        print(f"🔗 Connecting to Supabase: {url[:30]}...")
        self.supabase = create_client(url, key)

        print("🤖 Loading sentence transformer model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

        print("✅ Semantic search ready!\n")

    def check_embeddings_exist(self):
        """Check if any articles have embeddings"""
        try:
            response = self.supabase.table('press_releases')\
                .select('id, embedding')\
                .not_.is_('embedding', 'null')\
                .limit(1)\
                .execute()
            
            has_embeddings = len(response.data) > 0
            
            if has_embeddings:
                print("✅ Found embeddings in database")
            else:
                print("⚠️  No embeddings found. Run nlp_pipeline_fixed.py first to generate embeddings.")
            
            return has_embeddings
        except Exception as e:
            print(f"⚠️  Error checking embeddings: {e}")
            return False

    # def check_function_exists(self):
    #     """Check if match_articles function exists in Supabase"""
    #     try:
    #         # Try to call the function with dummy data
    #         self.supabase.rpc('match_articles', {
    #             'query_embedding': [0.0] * 384,
    #             'match_threshold': 0.9,
    #             'match_count': 1
    #         }).execute()
    #         print("✅ match_articles function exists")
    #         return True
    #     except Exception as e:
    #         if 'PGRST202' in str(e) or 'match_articles' in str(e):
    #             print("❌ match_articles function not found!")
    #             print("\n📝 You need to create it in Supabase:")
    #             print("   1. Go to Supabase SQL Editor")
    #             print("   2. Run the SQL from: create_semantic_search_function.sql")
    #             print("   3. Then run this script again\n")
    #             return False
    #         else:
    #             # Function exists but maybe there's another issue
    #             print(f"✅ match_articles function exists (validation returned: {e})")
    #             return True

    def search(self, query, threshold=0.5, limit=10):
        """
        Search for similar articles using semantic similarity
        
        Args:
            query: Search query text
            threshold: Similarity threshold (0-1, higher = more similar)
            limit: Maximum number of results to return
        """
        print(f"\n🔍 Searching for: '{query}'")
        print(f"   Threshold: {threshold}, Limit: {limit}\n")

        # Generate embedding for the query
        print("🧮 Generating query embedding...")
        query_embedding = self.embedding_model.encode(query).tolist()

        # Search using the match_articles function
        try:
            response = self.supabase.rpc('match_articles', {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit
            }).execute()

            results = response.data

            if not results:
                print("❌ No results found. Try:")
                print("   • Lowering the threshold (e.g., 0.3)")
                print("   • Using different search terms")
                print("   • Checking if embeddings exist in database\n")
                return []

            print(f"✅ Found {len(results)} results:\n")
            print("=" * 80)

            for i, result in enumerate(results, 1):
                print(f"\n{i}. {result['title']}")
                print(f"   Similarity: {result['similarity']:.3f}")
                print(f"   Date: {result.get('created_at', 'N/A')}")
                if result.get('url'):
                    print(f"   URL: {result['url']}")
                
                # Show snippet of summary or body
                content = result.get('summary') 
                if content:
                    snippet = content[:200] + "..." if len(content) > 200 else content
                    print(f"   Preview: {snippet}")
                
                print("-" * 80)

            return results

        except Exception as e:
            print(f"❌ Search failed: {e}")
            return []

    def search_interactive(self):
        """Interactive search mode"""
        print("\n" + "=" * 80)
        print("🔍 INTERACTIVE SEMANTIC SEARCH")
        print("=" * 80)
        print("\nCommands:")
        print("  • Enter search query to search")
        print("  • 'quit' or 'exit' to quit")
        print("  • 'threshold X' to set similarity threshold (e.g., 'threshold 0.7')")
        print("  • 'limit X' to set result limit (e.g., 'limit 5')")
        print()

        threshold = 0.5
        limit = 10

        while True:
            try:
                query = input("🔍 Search> ").strip()

                if not query:
                    continue

                if query.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break

                if query.startswith('threshold '):
                    try:
                        threshold = float(query.split()[1])
                        print(f"✅ Threshold set to: {threshold}")
                    except:
                        print("❌ Invalid threshold. Use: threshold 0.7")
                    continue

                if query.startswith('limit '):
                    try:
                        limit = int(query.split()[1])
                        print(f"✅ Limit set to: {limit}")
                    except:
                        print("❌ Invalid limit. Use: limit 5")
                    continue

                # Perform search
                self.search(query, threshold=threshold, limit=limit)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")


def main():
    """Main function with example searches"""
    print("=" * 80)
    print("🔍 SEMANTIC SEARCH FOR FRAUD ARTICLES")
    print("=" * 80)

    searcher = SemanticSearcher()

    # Check prerequisites
    print("\n📋 Checking prerequisites...")
    print("-" * 80)
    
    has_embeddings = searcher.check_embeddings_exist()
    # has_function = searcher.check_function_exists()

    # if not has_function:
    #     print("\n⚠️  Setup incomplete. Please create the match_articles function first.")
    #     return

    if not has_embeddings:
        print("\n⚠️  No embeddings found. Run nlp_pipeline_fixed.py first.")
        response = input("\nContinue anyway? (y/n): ").strip().lower()
        if response != 'y':
            return

    # Example searches
    print("\n" + "=" * 80)
    print("📚 EXAMPLE SEARCHES")
    print("=" * 80)

    example_queries = [
        ("AI fraud deepfakes", 0.5, 5),
        ("credit card scams", 0.4, 5),
        ("identity theft protection", 0.5, 5)
    ]

    for query, threshold, limit in example_queries:
        searcher.search(query, threshold=threshold, limit=limit)
        print("\n")

    # Interactive mode
    response = input("Would you like to try interactive search? (y/n): ").strip().lower()
    if response == 'y':
        searcher.search_interactive()


if __name__ == "__main__":
    main()