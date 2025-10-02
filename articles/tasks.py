from celery.utils.log import get_task_logger
from celery import shared_task
from time import sleep
from django.conf import settings

import os

from nomic import embed
import numpy as np
from datetime import datetime

from analyst.emails.notifications import send_latest_articles_email
from pymongo import MongoClient

from analyst.scrapers import ekapija, biznisrs

EMBEDDING_BATCH_SIZE = 10


logger = get_task_logger(__name__)

# Initialize Nomic client
os.environ['NOMIC_API_KEY'] = settings.NOMIC_API_KEY


def get_mongodb_connection():
    """Get MongoDB connection using settings from Django or environment variables."""
    mongo_uri = getattr(
        settings,
        "MONGODB_URI",
        os.getenv("MONGO_URI", "mongodb://localhost:8818/?directConnection=true"),
    )
    mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))
    mongo_collection = getattr(
        settings, "MONGO_COLLECTION", os.getenv("MONGO_COLLECTION", "articles")
    )

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    collection = db[mongo_collection]

    return client, collection


@shared_task
def test_task():
    logger.info("Task started")
    sleep(5)
    logger.info("Task completed")


@shared_task(max_retries=3, name="scrape_ekapija")
def scrape_ekapija():
    ekapija.main()
    return "Scraping Ekapija started"

@shared_task(max_retries=3, name="scrape_biznisrs")
def scrape_biznisrs():
    biznisrs.main()
    return "Scraping Biznisrs started"

@shared_task(bind=True, max_retries=3, name="create_all_embeddings")
def create_all_embeddings(
    self, batch_size: int = EMBEDDING_BATCH_SIZE, limit: int = None
):
    """
    Create embeddings for all articles that don't have them.

    Args:
        batch_size: Number of articles to process per Nomic API call
        limit: Maximum total number of articles to process

    Returns:
        Dict with processing statistics
    """
    client = None

    try:
        client, collection = get_mongodb_connection()

        # Query for articles that need embeddings
        # Only embed articles that have Italian title and content (since that's what we use)
        query = {
            "$and": [
                # No existing embedding
                {"embedding": {"$exists": False}},
                # Must have Italian title and content (required for embedding)
                {"title_it": {"$exists": True, "$ne": None, "$ne": ""}},
                {"content_it": {"$exists": True, "$ne": None, "$ne": ""}}
            ]
        }

        total_need_embedding = collection.count_documents(query)

        if total_need_embedding == 0:
            return {
                "status": "success",
                "message": "All articles already have embeddings",
                "total": 0,
            }

        # Process in batches
        articles_to_process = min(
            limit if limit else total_need_embedding, total_need_embedding
        )
        processed = 0
        failed = 0

        logger.info(f"Starting to create embeddings for {articles_to_process} articles")
        #sleep(30)  # Brief pause before starting

        while processed + failed < articles_to_process:
            # Get batch of articles
            articles = list(collection.find(query).limit(batch_size))

            if not articles:
                break

            # Prepare texts for batch embedding
            texts = []
            article_ids = []

            for article in articles:
                title_it = article.get("title_it")
                content_it = article.get("content_it")
                sector = article.get("sector", "")

                embedding_text = f"""
                Title: {title_it}
                Content: {content_it}
                Sector: {sector}
                """.strip()

                # Truncate if needed
                if len(embedding_text) > 8000:
                    embedding_text = embedding_text[:8000]

                texts.append(embedding_text)
                article_ids.append(article["_id"])

            try:
                # Nomic has more generous rate limits, but we'll still be conservative
                rate_limit_sleep = 2  # 2 seconds between requests (much more generous than VoyageAI)
                
                logger.info(f"Creating embeddings for batch of {len(texts)} articles")
                logger.info(f"Waiting {rate_limit_sleep} seconds between requests")
                sleep(rate_limit_sleep)

                # Use Nomic embed API
                result = embed.text(
                    texts=texts, 
                    model='nomic-embed-text-v1.5', 
                    task_type='search_document',
                    dimensionality=768  # Full dimensionality for best performance
                )

                # Update each article with its embedding
                for idx, (article_id, embedding) in enumerate(
                    zip(article_ids, result['embeddings'])
                ):
                    try:
                        collection.update_one(
                            {"_id": article_id},
                            {
                                "$set": {
                                    "embedding": embedding,
                                    "embedding_model": "nomic-embed-text-v1.5",
                                    "embedding_created_at": datetime.utcnow(),
                                    "embedding_dimensions": len(embedding),
                                }
                            },
                        )
                        processed += 1
                    except Exception as e:
                        logger.error(f"Failed to update article {article_id}: {str(e)}")
                        failed += 1

                logger.info(
                    f"✅ Processed batch: {processed} successful, {failed} failed"
                )

            except Exception as e:
                error_message = str(e).lower()
                
                # Check if it's a rate limit error
                if "rate limit" in error_message or "429" in error_message or "too many requests" in error_message:
                    logger.warning(f"Rate limit hit: {str(e)}")
                    logger.info("Waiting 70 seconds before retrying (rate limit recovery)")
                    sleep(70)  # Wait longer for rate limit to reset
                    
                    # Retry the batch once
                    try:
                        logger.info(f"Retrying batch of {len(texts)} articles after rate limit")
                        result = embed.text(
                            texts=texts, 
                            model='nomic-embed-text-v1.5', 
                            task_type='search_document',
                            dimensionality=768
                        )
                        
                        # Update each article with its embedding
                        for idx, (article_id, embedding) in enumerate(
                            zip(article_ids, result['embeddings'])
                        ):
                            try:
                                collection.update_one(
                                    {"_id": article_id},
                                    {
                                        "$set": {
                                            "embedding": embedding,
                                            "embedding_model": "nomic-embed-text-v1.5",
                                            "embedding_created_at": datetime.utcnow(),
                                            "embedding_dimensions": len(embedding),
                                        }
                                    },
                                )
                                processed += 1
                            except Exception as update_e:
                                logger.error(f"Failed to update article {article_id}: {str(update_e)}")
                                failed += 1
                        
                        logger.info(f"✅ Retry successful: {len(texts)} articles processed")
                        
                    except Exception as retry_e:
                        logger.error(f"Retry also failed: {str(retry_e)}")
                        failed += len(texts)
                else:
                    logger.error(f"Batch embedding failed: {str(e)}")
                    failed += len(texts)

                # Mark all in batch as failed
                # for article_id in article_ids:
                #     collection.update_one(
                #         {"_id": article_id},
                #         {
                #             "$set": {
                #                 "embedding_error": str(e),
                #                 "embedding_failed_at": datetime.utcnow(),
                #             }
                #         },
                #     )

        return {
            "status": "success",
            "message": "Embedding creation completed",
            "total_processed": processed,
            "total_failed": failed,
            "remaining": total_need_embedding - processed - failed,
        }

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    finally:
        if client:
            client.close()
