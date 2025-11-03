# Hugging Face Multilingual Reranking for Article Search

This document explains how to use the multilingual reranking functionality based on Hugging Face Transformers. This approach is specifically optimized for Italian content and provides high-quality reranking with minimal setup.

## What is Reranking?

Reranking is a process used to improve search results by applying a secondary model (reranker) to reorder the initial results from a vector search. While vector search is excellent for finding semantically similar content, rerankers can provide more accurate results by:

1. Taking the entire document content into account
2. Better understanding the relationship between query and document
3. Making more nuanced relevance judgments

## Installation

The reranking functionality relies on the `transformers` library from Hugging Face, which provides direct access to powerful multilingual models. To install:

```bash
# Install using pip
pip install -r requirements.txt
```

## How It Works

1. **Initial Vector Search**: First, the system performs a vector search using the multilingual-e5-base model to find potentially relevant documents.
2. **Reranking**: These candidate documents are then passed to a multilingual reranker, which reorders them based on relevance to the query.
3. **Result Presentation**: The reordered results are presented to the user.

The integration happens automatically in the `perform_vector_search` function, which now has a new parameter `apply_reranking` (default: `True`).

## Testing the Reranking

We've included a test script (`test_reranking.py`) that allows you to compare search results with and without reranking:

```bash
# Basic usage
python test_reranking.py "your search query"

# Compare with and without reranking
python test_reranking.py "your search query" --compare

# Disable reranking
python test_reranking.py "your search query" --no-reranking

# Limit the number of results
python test_reranking.py "your search query" --limit 5
```

## Performance Considerations

The reranking process uses the `cross-encoder/ms-marco-MiniLM-L-6-v2` model, which works well for multilingual content including Italian. It provides a good balance between quality and efficiency for reranking search results.

For very large result sets or in performance-critical scenarios, you can disable reranking by setting `apply_reranking=False` in the `perform_vector_search` function.

## Supported Languages

The integrated reranker is multilingual, supporting all major European languages including English, Italian, Serbian, and many others. It performs well across these languages without requiring any specific configuration.

## Customizing the Reranker

If you want to use a different reranking model, you can modify the `_load_reranker` method in `articles/reranking.py`:

```python
def _load_reranker(self):
    """Load the reranker model."""
    try:
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        # Create the model and tokenizer directly from Hugging Face
        self._tokenizer = AutoTokenizer.from_pretrained("cross-encoder/ms-marco-MiniLM-L-6-v2")
        self._model = AutoModelForSequenceClassification.from_pretrained("cross-encoder/ms-marco-MiniLM-L-6-v2")
        
        # Move to CPU for standard server deployment
        self._model.to("cpu")
        
        logger.info("Loaded Hugging Face reranker model successfully")
    except ImportError:
        logger.error("Failed to import transformers library")
        self._model = None
        self._tokenizer = None
```

## Troubleshooting

If you encounter any issues with the reranking functionality:

1. Check that the `transformers` library is properly installed
2. Run `python test_huggingface_reranker.py` to test the reranker directly
3. If you need to use premium Hugging Face models, run `python huggingface_token_setup.py` to set up your token
4. If the reranking consistently fails, the system will fall back to the original vector search results
