"""
Utility functions for the articles app.
"""

import os
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

# Initialize E5 model globally for reuse
_e5_model = None

def get_e5_model():
    """Get or initialize the E5 model."""
    global _e5_model
    if _e5_model is None:
        logger.info("Loading multilingual-e5-base model...")
        _e5_model = SentenceTransformer('intfloat/multilingual-e5-base')
        logger.info("Model loaded successfully")
    return _e5_model


def generate_query_embedding(
    query: str,
    model_name: str = "multilingual-e5-base",
    prefix: str = "query: ",
) -> Optional[List[float]]:
    """
    Generate an embedding vector for a search query using multilingual-e5-base model.
    """
    try:
        model = get_e5_model()
        prefixed_query = f"{prefix}{query}"
        embedding = model.encode(prefixed_query, show_progress_bar=False)
        return embedding.tolist()
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.
    
    Returns a value between -1 and 1, where 1 means identical direction.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def perform_vector_search(
    query: str,
    article_model,
    index_name: str = "article_vector_index",  # Kept for API compatibility
    num_candidates: int = 50,  # Kept for API compatibility
    limit: int = 18,
) -> List[Dict[str, Any]]:
    """
    Perform vector search using Python-based cosine similarity.
    
    This implementation works with any MongoDB version and doesn't require Atlas.
    Uses in-memory similarity calculation which is fast for datasets up to ~100k documents.
    
    Args:
        query: Search query text
        article_model: Django model class for articles
        index_name: (ignored, kept for API compatibility)
        num_candidates: (ignored, kept for API compatibility)
        limit: Maximum number of results to return
    
    Returns:
        List of article dictionaries with similarity scores
    """
    try:
        logger.info(f"Performing vector search for query: {query[:50]}...")
        
        # Generate query embedding
        query_embedding = generate_query_embedding(query)
        
        # Get all articles that have embeddings
        # Filter at DB level to reduce data transfer
        articles = list(article_model.objects.filter(
            embedding__exists=True,
            embedding__ne=None,
            embedding__type="array"  # Ensure it's an array
        ))
        
        logger.info(f"Found {len(articles)} articles with embeddings")
        
        if not articles:
            logger.warning("No articles with embeddings found")
            return []
        
        # Calculate similarity scores
        results = []
        for article in articles:
            try:
                if hasattr(article, 'embedding') and article.embedding:
                    # Calculate cosine similarity
                    similarity = cosine_similarity(query_embedding, article.embedding)
                    
                    # Only include articles with positive similarity (relevant)
                    if similarity > 0:
                        # Convert article to dictionary
                        article_dict = {
                            '_id': str(article.id if hasattr(article, 'id') else article._id),
                            'id': str(article.id if hasattr(article, 'id') else article._id),
                            'title_en': getattr(article, 'title_en', None),
                            'title_it': getattr(article, 'title_it', None),
                            'content_en': getattr(article, 'content_en', None),
                            'content_it': getattr(article, 'content_it', None),
                            'sector': getattr(article, 'sector', None),
                            'source': getattr(article, 'source', None),
                            'date': getattr(article, 'date', None),
                            'url': getattr(article, 'url', None),
                            'status': getattr(article, 'status', None),
                            'score': similarity * 100,  # Convert to percentage (0-100)
                        }
                        results.append(article_dict)
            except Exception as e:
                logger.warning(f"Error processing article {article.id}: {str(e)}")
                continue
        
        # Sort by similarity score (highest first)
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Return top N results
        top_results = results[:limit]
        
        # Log results with simplified syntax
        scores_preview = [round(r['score'], 1) for r in top_results[:5]]
        logger.info(f"Returning {len(top_results)} results (scores: {scores_preview})")
        
        return top_results
        
    except Exception as e:
        logger.error(f"Error performing vector search: {str(e)}", exc_info=True)
        raise


# Legacy functions kept for backwards compatibility
def build_vector_search_pipeline(
    query_embedding: List[float],
    index_name: str = "article_vector_index",
    embedding_path: str = "embedding",
    num_candidates: int = 50,
    limit: int = 18,
) -> List[Dict[str, Any]]:
    """
    Build a MongoDB aggregation pipeline for vector search.
    
    NOTE: This requires MongoDB Atlas or Community Edition 8.2+ with mongot.
    Currently not used - using Python-based search instead.
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
    
    Note: Currently not used since perform_vector_search returns normalized results.
    Kept for backwards compatibility.
    """
    processed_results = []

    for result in results:
        if isinstance(result, dict):
            item = dict(result)
            try:
                item["score"] = float(item.get("score", 0)) * 100
            except (TypeError, ValueError):
                item["score"] = 0
            if "_id" in item:
                item["_id"] = str(item["_id"])
                item["id"] = item["_id"]
            processed_results.append(item)
        else:
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
            item["id"] = getattr(result, "id", item["_id"]) or item["_id"]
            try:
                item["score"] = float(getattr(result, "score", 0)) * 100
            except (TypeError, ValueError):
                item["score"] = 0
            processed_results.append(item)

    return processed_results