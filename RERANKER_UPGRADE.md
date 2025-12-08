# Reranker Upgrade Guide

## Upgraded Model: BAAI/bge-reranker-v2-m3

### What Changed

- **Old Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2` (93M parameters)
- **New Model**: `BAAI/bge-reranker-v2-m3` (568M parameters)

### Why This Upgrade?

The BAAI/bge-reranker-v2-m3 model provides:

1. **Superior Multilingual Support**

   - Supports 100+ languages natively
   - Excellent performance on Italian, Serbian, and English
   - Cross-lingual retrieval capabilities

2. **Better Performance**

   - State-of-the-art reranking quality
   - Top performance on MTEB benchmark
   - Significantly better relevance scoring

3. **Optimized for Your Use Case**
   - Designed for multilingual document retrieval
   - Handles long documents better (up to 8192 tokens)
   - Better understanding of domain-specific content

### Performance Comparison

| Metric     | ms-marco-MiniLM | bge-reranker-v2-m3 |
| ---------- | --------------- | ------------------ |
| Parameters | 93M             | 568M               |
| Languages  | Limited         | 100+               |
| Max Length | 512 tokens      | 8192 tokens        |
| NDCG@10    | 0.39            | 0.56+              |

## Deployment Steps

### 1. Download the New Model

```bash
# Option A: Download directly in Django
docker exec ta_web python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"

# Option B: Pre-download using huggingface-cli
docker exec ta_web huggingface-cli download BAAI/bge-reranker-v2-m3
```

### 2. Test the Reranker

```bash
# Run the test script
docker exec ta_web python test_reranker.py

# Or test within your Django environment
docker exec ta_web python manage.py shell
```

In the shell:

```python
from articles.reranker import Reranker

# Initialize new reranker
reranker = Reranker()
print(f"Model loaded: {reranker.model_name}")
print(f"Available: {reranker.is_available()}")
```

### 3. Clear Old Model Cache (Optional)

```bash
# Remove old model to save disk space
docker exec ta_web python -c "
import shutil
from pathlib import Path
cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
old_model = cache_dir / 'models--cross-encoder--ms-marco-MiniLM-L-6-v2'
if old_model.exists():
    shutil.rmtree(old_model)
    print('Old model cache removed')
"
```

### 4. Restart the Application

```bash
# Restart to load the new model
docker restart ta_web
```

## Model Details

### BAAI/bge-reranker-v2-m3 Specifications

- **Architecture**: XLM-RoBERTa-based cross-encoder
- **Training Data**: Multilingual corpus from 100+ languages
- **Input**: Query-document pairs
- **Output**: Relevance score (higher = more relevant)
- **License**: MIT (free for commercial use)

### Supported Languages Include:

- English, Italian, Serbian, German, French, Spanish
- Russian, Chinese, Japanese, Korean, Arabic
- And 90+ more languages

## Expected Improvements

After upgrading, you should see:

1. **Better Relevance**: More accurate reranking of search results
2. **Multilingual Queries**: Better handling of cross-language searches
3. **Domain Understanding**: Improved understanding of business/economic content
4. **Long Documents**: Better handling of lengthy articles

## Fallback Behavior

The reranker implementation includes automatic fallbacks:

1. Primary: sentence-transformers CrossEncoder (recommended)
2. Fallback 1: transformers AutoModel (if CrossEncoder fails)
3. Fallback 2: Text-based matching (if ML models fail)

This ensures search continues working even if the model fails to load.

## Performance Considerations

- **Model Size**: ~2.3GB (vs. ~400MB for old model)
- **Inference Speed**: Slightly slower but still fast enough for real-time use
- **Memory**: ~3GB RAM during inference
- **CPU**: Works fine on CPU, GPU optional

For production with high traffic, consider:

- Caching reranked results
- Using batch processing for large result sets
- Adjusting `num_candidates` in vector search

## Monitoring

Check reranker performance in logs:

```bash
docker logs ta_web | grep -i rerank
```

You should see:

```
Loaded BAAI/bge-reranker-v2-m3 using sentence-transformers
Reranking X results
Reranked using sentence-transformers CrossEncoder
```

## Rollback (if needed)

If you need to rollback to the old model:

```python
# In articles/reranker.py, change line 25 back to:
def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
```

Then restart the application.
