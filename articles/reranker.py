"""
Consolidated reranking implementation using sentence-transformers.
This file provides a robust reranking solution with fallback mechanisms
for improved search result ranking.
"""

import logging
import torch
from typing import List, Dict, Any, Optional
import re

# Configure logging
logging.basicConfig(format="%(asctime)s [%(name)s] %(levelname)s: %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

class Reranker:
    """
    Unified reranker with multiple implementation strategies and fallbacks.
    Uses CrossEncoder from sentence-transformers as the primary implementation.
    """
    
    # Singleton model instances
    _cross_encoder = None
    
    def __init__(self, model_name="mixedbread-ai/mxbai-rerank-xsmall-v1"):
        """
        Initialize the reranker with specified model.
        
        Default model changed to mixedbread-ai/mxbai-rerank-xsmall-v1 for better speed.
        This is 4x faster than the previous BAAI/bge-reranker-v2-m3 model.
        
        Other options:
        - "mixedbread-ai/mxbai-rerank-xsmall-v1" (fastest, good quality)
        - "BAAI/bge-reranker-base" (medium speed, good quality)
        - "BAAI/bge-reranker-v2-m3" (slowest, best quality)
        """
        self.model_name = model_name
        
        if Reranker._cross_encoder is None:
            self._load_model()
    
    def _load_model(self):
        """Load the cross-encoder model."""
        try:
            # First try to load using sentence-transformers (recommended)
            from sentence_transformers import CrossEncoder
            Reranker._cross_encoder = CrossEncoder(self.model_name, device='cpu')
            logger.info(f"Loaded {self.model_name} using sentence-transformers")
        except Exception as e:
            logger.warning(f"Failed to load model with sentence-transformers: {str(e)}")
            Reranker._cross_encoder = None
            
            # Try loading with transformers directly as fallback
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                
                logger.info(f"Attempting to load {self.model_name} using transformers directly")
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                self._model.to("cpu")
                
                # Store in a dictionary for the fallback implementation
                Reranker._cross_encoder = {
                    'tokenizer': self._tokenizer,
                    'model': self._model
                }
                logger.info(f"Loaded {self.model_name} using transformers directly")
            except Exception as e2:
                logger.error(f"Failed to load model with transformers: {str(e2)}")
                Reranker._cross_encoder = None
    
    def is_available(self) -> bool:
        """Check if any reranking implementation is available."""
        return Reranker._cross_encoder is not None
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for the fallback implementation."""
        # Convert to lowercase and replace non-alphanumeric with space
        text = re.sub(r'[^\w\s]', ' ', text.lower())
        # Split by whitespace and filter out empty strings
        return [token for token in text.split() if token]
    
    def _calculate_fallback_score(self, query_tokens: List[str], doc_text: str) -> float:
        """Calculate a simple relevance score based on token matching."""
        doc_text_lower = doc_text.lower()
        
        # Base score components
        exact_match_score = 0
        token_match_score = 0
        position_score = 0
        
        # Check for exact phrase match (highest importance)
        query_phrase = ' '.join(query_tokens)
        if query_phrase in doc_text_lower:
            # Give higher score for exact matches
            exact_match_score = 10.0
            # Position bonus - earlier matches are better
            position = doc_text_lower.find(query_phrase)
            position_score = max(0, 5.0 - (position / 100.0))
        
        # Count individual token matches
        doc_tokens = self._tokenize(doc_text)
        total_matches = 0
        
        for query_token in query_tokens:
            if query_token in doc_tokens:
                total_matches += 1
                # Add bonus for frequency
                token_match_score += doc_tokens.count(query_token) * 0.2
        
        # Calculate percentage of query tokens found
        if query_tokens:
            coverage = total_matches / len(query_tokens)
            token_match_score += coverage * 5.0
        
        # Combine all scores
        final_score = exact_match_score + token_match_score + position_score
        
        # Normalize to a 0-1 range (approximately)
        normalized_score = min(1.0, final_score / 20.0)
        
        return normalized_score
    
    def rerank(self, query: str, docs: List[Dict[str, Any]], 
               content_field: str = 'content_it', 
               title_field: str = 'title_it',
               limit: int = 18) -> List[Dict[str, Any]]:
        """
        Rerank documents based on the query.
        
        Args:
            query: Search query
            docs: List of documents from vector search
            content_field: Field name for document content
            title_field: Field name for document title
            limit: Maximum number of results to return
            
        Returns:
            Reranked documents
        """
        if not docs:
            return []
        
        try:
            # Create document texts for reranking by combining title and content
            document_texts = []
            for doc in docs:
                # Get title and content, fallback to alternative fields if needed
                title = (doc.get(title_field) or doc.get('title_en') or 
                        doc.get('title_rs') or 'No title')
                
                # Get a snippet of content for reranking (first 500 chars for speed)
                content = doc.get(content_field) or doc.get('content_en') or doc.get('content_rs') or ''
                content = content[:500]  # Truncate to 500 chars for faster processing
                
                # Combine title and content for better reranking
                text = f"{title}\n{content}"
                document_texts.append(text)
            
            scores = None
            
            # Try using the cross-encoder from sentence-transformers
            if isinstance(Reranker._cross_encoder, object) and hasattr(Reranker._cross_encoder, 'predict'):
                try:
                    # Create sentence pairs for CrossEncoder
                    sentence_pairs = [[query, doc_text] for doc_text in document_texts]
                    scores = Reranker._cross_encoder.predict(sentence_pairs)
                    logger.info("Reranked using sentence-transformers CrossEncoder")
                except Exception as e:
                    logger.error(f"Error using CrossEncoder predict: {str(e)}")
            
            # Try using the transformers implementation if CrossEncoder failed
            if scores is None and isinstance(Reranker._cross_encoder, dict):
                try:
                    tokenizer = Reranker._cross_encoder['tokenizer']
                    model = Reranker._cross_encoder['model']
                    
                    # Get scores using batched inference
                    scores = []
                    batch_size = 16  # Increased batch size for better throughput
                    
                    for i in range(0, len(document_texts), batch_size):
                        batch_queries = [query] * min(batch_size, len(document_texts) - i)
                        batch_docs = document_texts[i:i+batch_size]
                        
                        # Tokenize batch
                        features = tokenizer(
                            batch_queries,
                            batch_docs,
                            padding=True,
                            truncation=True,
                            return_tensors="pt",
                            max_length=128  # Reduced to 128 for faster processing
                        )
                        
                        # Get scores
                        with torch.no_grad():
                            outputs = model(**features)
                            batch_scores = outputs.logits.squeeze(-1).tolist()
                            if not isinstance(batch_scores, list):
                                batch_scores = [batch_scores]
                            scores.extend(batch_scores)
                    
                    logger.info("Reranked using transformers implementation")
                except Exception as e:
                    logger.error(f"Error using transformers for reranking: {str(e)}")
                    scores = None
            
            # Use fallback text-matching implementation if ML methods failed
            if scores is None:
                logger.info("Using fallback text-matching reranker")
                scores = []
                query_tokens = self._tokenize(query)
                for text in document_texts:
                    score = self._calculate_fallback_score(query_tokens, text)
                    scores.append(score)
            
            # Create reranked results
            result_docs = []
            for i, score in enumerate(scores):
                # Get original document and add rerank score
                orig_doc = docs[i].copy()  # Use a copy to avoid modifying original
                orig_doc['rerank_score'] = float(score)
                result_docs.append(orig_doc)
            
            # Sort by score in descending order
            result_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Add rank field
            for i, doc in enumerate(result_docs, 1):
                doc['rank'] = i
            
            # Return top results
            return result_docs[:limit]
            
        except Exception as e:
            logger.error(f"Error during reranking: {str(e)}")
            # Fall back to original docs without reranking
            return docs[:limit] if docs else []

def rerank_search_results(query: str, vector_search_results: List[Dict[str, Any]], 
                       limit: int = 18) -> List[Dict[str, Any]]:
    """
    Rerank vector search results using the unified reranker.
    
    Args:
        query: The search query text
        vector_search_results: Results from vector search
        limit: Maximum number of results to return
        
    Returns:
        Reranked search results
    """
    reranker = Reranker()
    
    if not reranker.is_available():
        # Return original results if reranker not available
        logger.warning("Reranker not available, returning original vector search results")
        return vector_search_results[:limit]
    
    logger.info(f"Reranking {len(vector_search_results)} results")
    return reranker.rerank(
        query=query,
        docs=vector_search_results,
        content_field='content_it',
        title_field='title_it',
        limit=limit
    )
