# Creating Atlas Search Index

Follow these steps to create the Atlas Search index for the articles collection:

## Option 1: Using MongoDB Atlas UI

1. Log in to MongoDB Atlas (https://cloud.mongodb.com)
2. Navigate to your cluster
3. Click on the "Search" tab
4. Click "Create Search Index"
5. Choose "JSON Editor"
6. Set the following:
   - **Database**: `analyst` (or your database name)
   - **Collection**: `articles`
   - **Index Name**: `article_text_search_index`
7. Paste the contents of `atlas_search_index.json` into the JSON editor
8. Click "Create Search Index"

## Option 2: Using MongoDB Compass

1. Open MongoDB Compass
2. Connect to your MongoDB Atlas cluster
3. Navigate to the `articles` collection
4. Click on the "Search Indexes" tab
5. Click "Create Search Index"
6. Name it: `article_text_search_index`
7. Paste the contents of `atlas_search_index.json`
8. Click "Create Search Index"

## Option 3: Using mongosh CLI

```javascript
use analyst  // or your database name

db.articles.createSearchIndex(
  "article_text_search_index",
  {
    "mappings": {
      "dynamic": false,
      "fields": {
        "title_it": { "type": "string", "analyzer": "lucene.italian" },
        "content_it": { "type": "string", "analyzer": "lucene.italian" },
        "sector": { "type": "string", "analyzer": "lucene.standard" },
        "source": { "type": "string", "analyzer": "lucene.keyword" },
        "status": { "type": "string", "analyzer": "lucene.keyword" },
        "article_date": { "type": "date" },
        "scraped_at": { "type": "date" }
      }
    }
  }
)
```

## Verify Index Creation

After creating the index, it may take a few minutes to build. You can check the status in:

- Atlas UI: Search tab → Index status
- Compass: Search Indexes tab

The index is ready when the status shows "Active".

## Index Details

- **Name**: `article_text_search_index`
- **Purpose**: Full-text search across Italian article titles and content
- **Language**: Italian only (using lucene.italian analyzer)
- **Additional Fields**: sector, source, status for filtering
- **Date Fields**: article_date and scraped_at for temporal queries

## Using with Hybrid Search

This index works alongside the existing vector search index (`article_vector_index`) to provide:

- **Text Search**: Keyword-based relevance using Atlas Search
- **Semantic Search**: Meaning-based similarity using Vector Search
- **Hybrid Search**: Combined results from both methods for best accuracy
