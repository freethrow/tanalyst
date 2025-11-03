# Reranking Implementation

This document describes the consolidated reranking implementation used in the project.

## Overview

The reranker improves search results by re-ordering documents based on their relevance to the query. It uses a cross-encoder model to score query-document pairs and produces better ranking than vector search alone.

## Features

- **Unified implementation**: Combines multiple approaches into a single file
- **Multiple fallback mechanisms**: If one method fails, it tries alternatives
- **Efficient resource usage**: Optimized for CPU-only environments
- **Simple API**: Easy to use with a single function call

## Usage

```python
from articles.reranker import rerank_search_results

# After performing vector search:
reranked_results = rerank_search_results(
    query="user search query",
    vector_search_results=vector_results,
    limit=10
)
```

## Implementation Details

The reranker uses a tiered approach:

1. First tries the `sentence-transformers` CrossEncoder (most efficient)
2. Falls back to direct `transformers` implementation if the first method fails
3. Uses a simple text-matching algorithm as a last resort

## Model

Uses the `cross-encoder/ms-marco-MiniLM-L-6-v2` model which:
- Is optimized for passage ranking
- Supports multiple languages, including Italian
- Has a good balance of performance and efficiency

## Dependencies

All required dependencies are in requirements.txt:
- sentence-transformers
- transformers
- torch (CPU version)
- huggingface-hub
