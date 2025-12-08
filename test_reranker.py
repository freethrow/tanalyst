#!/usr/bin/env python
"""
Simple test script for the consolidated reranker implementation.
"""
import time
import sys

def test_reranker():
    """Test the consolidated reranker implementation."""
    print("\nTesting consolidated reranker...\n")
    
    try:
        from articles.reranker import Reranker, rerank_search_results
        
        # Load the model
        print("Loading reranker model...")
        start_time = time.time()
        reranker = Reranker('BAAI/bge-reranker-v2-m3')
        load_time = time.time() - start_time
        print(f"Model loaded in {load_time:.2f} seconds")
        print(f"Reranker available: {reranker.is_available()}")
        
        # Test with Italian content
        query = "economia italiana"
        docs = [
            {
                "title_it": "Crescita economica in Italia nel 2025",
                "content_it": "L'economia italiana mostra segni di crescita nel 2025, con un incremento del PIL del 1.8% rispetto all'anno precedente."
            },
            {
                "title_it": "Turismo in Croazia",
                "content_it": "La Croazia ha registrato un record di presenze turistiche durante l'estate 2024, superando le cifre pre-pandemia."
            },
            {
                "title_it": "Sviluppo del settore agricolo italiano",
                "content_it": "Il settore agricolo italiano ha beneficiato di nuovi investimenti e tecnologie innovative che hanno aumentato la produttività."
            },
            {
                "title_it": "Mercati finanziari europei",
                "content_it": "I mercati finanziari europei hanno mostrato volatilità a causa delle tensioni geopolitiche, ma l'Italia ha mantenuto stabilità."
            }
        ]
        
        # Perform ranking
        print(f"\nRanking documents with query: '{query}'")
        start_time = time.time()
        results = rerank_search_results(query=query, vector_search_results=docs)
        rank_time = time.time() - start_time
        
        # Show results
        print(f"\nResults (ranked in {rank_time:.4f} seconds):")
        for doc in results:
            print(f"{doc['rank']}. {doc['title_it']}")
            print(f"   Score: {doc['rerank_score']:.4f}")
        
        print("\nTest completed successfully!")
        return 0
        
    except ImportError as e:
        print(f"Error importing reranker: {e}")
        print("Make sure sentence-transformers is installed: pip install sentence-transformers")
        return 1
    except Exception as e:
        print(f"Error testing reranker: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(test_reranker())
