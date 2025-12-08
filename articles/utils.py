"""
Utility functions for the articles app.
"""

import os
from typing import List, Dict, Any, Optional
from django.conf import settings
from sentence_transformers import SentenceTransformer

# Initialize E5 model globally for reuse
_e5_model = None

def get_e5_model():
    """Get or initialize the E5 model."""
    global _e5_model
    if _e5_model is None:
        _e5_model = SentenceTransformer('intfloat/multilingual-e5-large')
    return _e5_model


def generate_query_embedding(
    query: str,
    model_name: str = "multilingual-e5-large",
    prefix: str = "query: ",
) -> Optional[List[float]]:
    """
    Generate an embedding vector for a search query using multilingual-e5-large model.

    Args:
        query: The search query text
        model_name: The model name identifier (default: multilingual-e5-large)
        prefix: The prefix to add to the query for E5 models (default: "query: ")

    Returns:
        List of floats representing the embedding vector, or None if error occurs

    Raises:
        Exception: If embedding generation fails
    """
    try:
        # Get or initialize the model
        model = get_e5_model()
        
        # E5 models work best with prefixes
        prefixed_query = f"{prefix}{query}"
        
        # Generate embedding
        embedding = model.encode(prefixed_query)
        
        # Convert to list of floats (from numpy array)
        return embedding.tolist()
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        raise


def build_vector_search_pipeline(
    query_embedding: List[float],
    index_name: str = "article_vector_index",
    embedding_path: str = "embedding",
    num_candidates: int = 50,
    limit: int = 18,
) -> List[Dict[str, Any]]:
    """
    Build a MongoDB aggregation pipeline for vector search.

    Args:
        query_embedding: The embedding vector to search for
        index_name: The name of the vector search index (default: article_vector_index)
        embedding_path: The field path containing embeddings (default: embedding)
        num_candidates: Number of candidates to consider (default: 50)
        limit: Maximum number of results to return (default: 18)

    Returns:
        MongoDB aggregation pipeline as a list of dictionaries
    """
    return [
        {
            "$vectorSearch": {
                "index": index_name,
                "path": embedding_path,
                "queryVector": query_embedding,
                "numCandidates": num_candidates,
                "limit": limit,
            }
        },
        {
            "$project": {
                "_id": 1,
                "score": {"$meta": "vectorSearchScore"},
                "title_en": 1,
                "title_it": 1,
                "content_en": 1,
                "content_it": 1,
                "sector": 1,
                "source": 1,
                "date": 1,
                "url": 1,
                "status": 1,
            }
        },
    ]


def normalize_search_results(results: List[Any]) -> List[Dict[str, Any]]:
    """
    Normalize vector search results to a consistent dictionary format.

    Handles both dictionary results and Article model instances.
    Converts scores to percentages and ObjectIds to strings.
    Adds rank field for position in search results.

    Args:
        results: Raw results from MongoDB aggregation

    Returns:
        List of normalized result dictionaries
    """
    processed_results = []

    for result in results:
        if isinstance(result, dict):
            item = dict(result)
            # Convert score to percentage (0-100)
            try:
                item["score"] = float(item.get("score", 0)) * 100
            except (TypeError, ValueError):
                item["score"] = 0
            # Convert ObjectId to string for template
            if "_id" in item:
                item["_id"] = str(item["_id"])
                # Also provide a generic 'id' for URL reversing
                item["id"] = item["_id"]
            processed_results.append(item)
        else:
            # It's likely an Article instance; map needed fields into a dict
            item = {
                "_id": str(getattr(result, "_id", getattr(result, "id", ""))),
                "title_en": getattr(result, "title_en", None),
                "title_it": getattr(result, "title_it", None),
                "content_en": getattr(result, "content_en", None),
                "content_it": getattr(result, "content_it", None),
                "sector": getattr(result, "sector", None),
                "source": getattr(result, "source", None),
                "date": getattr(result, "date", None),
                "url": getattr(result, "url", None),
            }
            # Provide 'id' for URL reversing
            item["id"] = getattr(result, "id", item["_id"]) or item["_id"]
            # Score might be present as an annotated attribute
            try:
                item["score"] = float(getattr(result, "score", 0)) * 100
            except (TypeError, ValueError):
                item["score"] = 0
            processed_results.append(item)

    # Add rank field (1-based index) to each result
    for i, item in enumerate(processed_results, 1):
        item['rank'] = i
        
    return processed_results


def perform_vector_search(
    query: str,
    article_model,
    index_name: str = "article_vector_index",
    num_candidates: int = 50,
    limit: int = 18,
    apply_reranking: bool = False,
) -> List[Dict[str, Any]]:
    """
    Perform a complete vector search operation.

    This is a high-level function that combines embedding generation,
    pipeline building, and result normalization.

    Args:
        query: The search query text
        article_model: The Article model class to query against
        index_name: The name of the vector search index
        num_candidates: Number of candidates to consider
        limit: Maximum number of results to return
        apply_reranking: Whether to apply reranking to improve results (default: False - disabled for speed)

    Returns:
        List of normalized search results

    Raises:
        Exception: If embedding generation or search fails
    """
    # Generate query embedding
    query_embedding = generate_query_embedding(query)

    # For reranking, fetch more candidates than needed for better results
    fetch_limit = num_candidates if apply_reranking else limit

    # Build search pipeline
    pipeline = build_vector_search_pipeline(
        query_embedding=query_embedding,
        index_name=index_name,
        num_candidates=num_candidates,
        limit=fetch_limit,
    )

    # Execute aggregation
    results = list(article_model.objects.raw_aggregate(pipeline))

    # Normalize results
    normalized_results = normalize_search_results(results)
    
    # Apply reranking if enabled and at least a few results available
    if apply_reranking and len(normalized_results) > 1:
        try:
            # Use our consolidated reranking implementation
            from articles.reranker import rerank_search_results
            return rerank_search_results(
                query=query,
                vector_search_results=normalized_results,
                limit=limit
            )
        except Exception as e:
            print(f"Reranking failed: {str(e)}")
            # If there's an error, simply use the original vector search results
    
    # Return normalized results (either without reranking or if reranking failed)
    return normalized_results[:limit]


def build_atlas_search_pipeline(
    query: str,
    index_name: str = "article_text_search_index",
    limit: int = 18,
    search_fields: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Build a MongoDB aggregation pipeline for Atlas Search (text search).

    Args:
        query: The search query text
        index_name: The name of the Atlas Search index (default: article_text_search_index)
        limit: Maximum number of results to return (default: 18)
        search_fields: List of fields to search in (default: Italian text fields only)

    Returns:
        MongoDB aggregation pipeline as a list of dictionaries
    """
    if search_fields is None:
        # Search only Italian fields
        search_fields = [
            "title_it",
            "content_it"
        ]
    
    return [
        {
            "$search": {
                "index": index_name,
                "text": {
                    "query": query,
                    "path": search_fields,
                    "fuzzy": {
                        "maxEdits": 1,
                        "prefixLength": 2
                    }
                }
            }
        },
        {
            "$limit": limit
        },
        {
            "$project": {
                "_id": 1,
                "score": {"$meta": "searchScore"},
                "title_en": 1,
                "title_it": 1,
                "content_en": 1,
                "content_it": 1,
                "sector": 1,
                "source": 1,
                "date": 1,
                "url": 1,
                "status": 1,
            }
        },
    ]


def perform_atlas_search(
    query: str,
    article_model,
    index_name: str = "article_text_search_index",
    limit: int = 18,
) -> List[Dict[str, Any]]:
    """
    Perform Atlas Search (full-text search) operation.

    Args:
        query: The search query text
        article_model: The Article model class to query against
        index_name: The name of the Atlas Search index
        limit: Maximum number of results to return

    Returns:
        List of normalized search results

    Raises:
        Exception: If search fails
    """
    # Build search pipeline
    pipeline = build_atlas_search_pipeline(
        query=query,
        index_name=index_name,
        limit=limit,
    )

    # Execute aggregation
    results = list(article_model.objects.raw_aggregate(pipeline))

    # Normalize results
    return normalize_search_results(results)


def normalize_hybrid_scores(
    vector_results: List[Dict[str, Any]],
    text_results: List[Dict[str, Any]],
    vector_weight: float = 0.5,
    text_weight: float = 0.5,
) -> List[Dict[str, Any]]:
    """
    Normalize and combine scores from vector and text search.

    Uses Reciprocal Rank Fusion (RRF) to combine rankings from both search methods.

    Args:
        vector_results: Results from vector search
        text_results: Results from Atlas text search
        vector_weight: Weight for vector search scores (default: 0.5)
        text_weight: Weight for text search scores (default: 0.5)

    Returns:
        Combined results with normalized hybrid scores
    """
    k = 60  # RRF constant (typical value)
    
    # Create result dictionaries for tracking
    result_map = {}
    
    # Process vector search results
    for rank, result in enumerate(vector_results, 1):
        doc_id = result.get('_id') or result.get('id')
        if not doc_id:
            continue
            
        result_map[doc_id] = {
            **result,
            'vector_rank': rank,
            'vector_score': result.get('score', 0),
            'text_rank': None,
            'text_score': 0,
            'search_type': 'vector'
        }
    
    # Process text search results
    for rank, result in enumerate(text_results, 1):
        doc_id = result.get('_id') or result.get('id')
        if not doc_id:
            continue
            
        if doc_id in result_map:
            # Document found in both searches
            result_map[doc_id]['text_rank'] = rank
            result_map[doc_id]['text_score'] = result.get('score', 0)
            result_map[doc_id]['search_type'] = 'hybrid'
        else:
            # Document only in text search
            result_map[doc_id] = {
                **result,
                'vector_rank': None,
                'vector_score': 0,
                'text_rank': rank,
                'text_score': result.get('score', 0),
                'search_type': 'text'
            }
    
    # Calculate RRF scores
    for doc_id, doc in result_map.items():
        rrf_score = 0
        
        if doc['vector_rank']:
            rrf_score += vector_weight / (k + doc['vector_rank'])
        
        if doc['text_rank']:
            rrf_score += text_weight / (k + doc['text_rank'])
        
        doc['hybrid_score'] = rrf_score * 100  # Scale to 0-100
        doc['score'] = doc['hybrid_score']  # Use hybrid score as main score
    
    # Sort by hybrid score
    combined_results = sorted(
        result_map.values(),
        key=lambda x: x['hybrid_score'],
        reverse=True
    )
    
    # Add final rank
    for rank, result in enumerate(combined_results, 1):
        result['rank'] = rank
    
    return combined_results


def perform_hybrid_search(
    query: str,
    article_model,
    vector_index_name: str = "article_vector_index",
    text_index_name: str = "article_text_search_index",
    limit: int = 18,
    vector_weight: float = 0.6,
    text_weight: float = 0.4,
    apply_reranking: bool = False,
) -> List[Dict[str, Any]]:
    """
    Perform hybrid search combining vector search and Atlas text search.

    This provides the best of both worlds:
    - Vector search finds semantically similar content
    - Atlas Search finds keyword matches
    - Results are combined using Reciprocal Rank Fusion

    Args:
        query: The search query text
        article_model: The Article model class to query against
        vector_index_name: Name of the vector search index
        text_index_name: Name of the Atlas text search index
        limit: Maximum number of results to return
        vector_weight: Weight for vector search (default: 0.6 - slightly favor semantic)
        text_weight: Weight for text search (default: 0.4)
        apply_reranking: Whether to apply reranking to final results (default: False - disabled for speed)

    Returns:
        List of hybrid search results with combined scores

    Raises:
        Exception: If either search fails
    """
    # Fetch more candidates for better hybrid results
    fetch_limit = limit * 2
    
    # Perform both searches in parallel (conceptually)
    try:
        vector_results = perform_vector_search(
            query=query,
            article_model=article_model,
            index_name=vector_index_name,
            num_candidates=100,
            limit=fetch_limit,
            apply_reranking=False,  # Don't rerank individual results yet
        )
    except Exception as e:
        print(f"Vector search failed: {str(e)}")
        vector_results = []
    
    try:
        text_results = perform_atlas_search(
            query=query,
            article_model=article_model,
            index_name=text_index_name,
            limit=fetch_limit,
        )
    except Exception as e:
        print(f"Atlas text search failed: {str(e)}")
        text_results = []
    
    # If both searches failed, raise an error
    if not vector_results and not text_results:
        raise Exception("Both vector and text search failed")
    
    # If only one search succeeded, return those results
    if not vector_results:
        return text_results[:limit]
    if not text_results:
        return vector_results[:limit]
    
    # Combine results using RRF
    hybrid_results = normalize_hybrid_scores(
        vector_results=vector_results,
        text_results=text_results,
        vector_weight=vector_weight,
        text_weight=text_weight,
    )
    
    # Apply reranking if enabled
    if apply_reranking and len(hybrid_results) > 1:
        try:
            from articles.reranker import rerank_search_results
            return rerank_search_results(
                query=query,
                vector_search_results=hybrid_results,
                limit=limit
            )
        except Exception as e:
            print(f"Reranking failed: {str(e)}")
    
    return hybrid_results[:limit]
