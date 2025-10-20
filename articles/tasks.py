from celery.utils.log import get_task_logger
from celery import shared_task
from time import sleep
from django.conf import settings

import os
import numpy as np
from datetime import datetime, timedelta

from articles.utils import get_e5_model

from analyst.emails.notifications import send_latest_articles_email
from pymongo import MongoClient
from django.utils import timezone

from analyst.scrapers import ekapija, biznisrs

# Import the summarizer module to register the task
from analyst.agents import summarizer

EMBEDDING_BATCH_SIZE = 10


logger = get_task_logger(__name__)


def get_mongodb_connection():
    """Get MongoDB connection using settings from Django or environment variables."""
    mongo_uri = getattr(settings, "MONGODB_URI", None)
    mongo_db = getattr(settings, "MONGO_DB", None)
    mongo_collection = getattr(settings, "MONGO_COLLECTION", None)

    if not mongo_uri or not mongo_db or not mongo_collection:
        raise RuntimeError(
            "MongoDB configuration missing. Ensure MONGODB_URI, MONGO_DB, and MONGO_COLLECTION are set in .env and loaded via settings."
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
                {"content_it": {"$exists": True, "$ne": None, "$ne": ""}},
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
        # sleep(30)  # Brief pause before starting

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
                rate_limit_sleep = (
                    2  # 2 seconds between requests (much more generous than VoyageAI)
                )

                logger.info(f"Creating embeddings for batch of {len(texts)} articles")
                logger.info(f"Waiting {rate_limit_sleep} seconds between requests")
                sleep(rate_limit_sleep)

                # Use E5 model for embeddings
                model = get_e5_model()
                
                # E5 models work best with passage prefix for documents
                prefixed_texts = [f"passage: {text}" for text in texts]
                
                # Generate embeddings for batch
                embeddings = model.encode(prefixed_texts)
                
                # Update each article with its embedding
                for idx, (article_id, embedding) in enumerate(
                    zip(article_ids, embeddings)
                ):
                    try:
                        collection.update_one(
                            {"_id": article_id},
                            {
                                "$set": {
                                    "embedding": embedding.tolist(),
                                    "embedding_model": "multilingual-e5-base",
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
                if (
                    "rate limit" in error_message
                    or "429" in error_message
                    or "too many requests" in error_message
                ):
                    logger.warning(f"Rate limit hit: {str(e)}")
                    logger.info(
                        "Waiting 70 seconds before retrying (rate limit recovery)"
                    )
                    sleep(70)  # Wait longer for rate limit to reset

                    # Retry the batch once
                    try:
                        logger.info(
                            f"Retrying batch of {len(texts)} articles after rate limit"
                        )
                        # Use E5 model for embeddings
                        model = get_e5_model()
                        
                        # E5 models work best with passage prefix for documents
                        prefixed_texts = [f"passage: {text}" for text in texts]
                        
                        # Generate embeddings for batch
                        embeddings = model.encode(prefixed_texts)

                        # Update each article with its embedding
                        for idx, (article_id, embedding) in enumerate(
                            zip(article_ids, embeddings)
                        ):
                            try:
                                collection.update_one(
                                    {"_id": article_id},
                                    {
                                        "$set": {
                                            "embedding": embedding.tolist(),
                                            "embedding_model": "multilingual-e5-base",
                                            "embedding_created_at": datetime.utcnow(),
                                            "embedding_dimensions": len(embedding),
                                        }
                                    },
                                )
                                processed += 1
                            except Exception as update_e:
                                logger.error(
                                    f"Failed to update article {article_id}: {str(update_e)}"
                                )
                                failed += 1

                        logger.info(
                            f"✅ Retry successful: {len(texts)} articles processed"
                        )

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


@shared_task(name="mark_old_articles_used")
def mark_old_articles_used(days_threshold=30):
    """
    Mark articles older than specified days as SENT (used in email).

    Args:
        days_threshold (int): Number of days after which articles should be marked as SENT (default: 30)

    Returns:
        dict: Status and count of updated articles
    """
    from articles.models import Article

    logger.info(
        f"Starting task to mark articles older than {days_threshold} days as SENT"
    )

    # Calculate the cutoff date
    cutoff_date = timezone.now() - timedelta(days=days_threshold)

    logger.info(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Find articles that are:
        # 1. Older than the threshold (based on article_date)
        # 2. Not already marked as SENT
        # 3. Have Italian content (to match the existing workflow)
        old_articles = (
            Article.objects.filter(
                article_date__lt=cutoff_date,
                title_it__isnull=False,
                content_it__isnull=False,
            )
            .exclude(status=Article.SENT)
            .exclude(title_it__exact="", content_it__exact="")
        )

        count = old_articles.count()

        if count == 0:
            logger.info(
                f"No articles found older than {days_threshold} days that need to be marked as SENT"
            )
            return {
                "status": "success",
                "message": f"No articles older than {days_threshold} days to mark as SENT",
                "updated_count": 0,
            }

        logger.info(f"Found {count} articles to mark as SENT")

        # Update the articles
        updated_count = 0
        for article in old_articles:
            article.status = Article.SENT
            article.save()
            updated_count += 1

        logger.info(f"Successfully marked {updated_count} articles as SENT")

        return {
            "status": "success",
            "message": f"Successfully marked {updated_count} articles as SENT",
            "updated_count": updated_count,
            "cutoff_date": cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),
        }

    except Exception as e:
        logger.error(f"Error marking old articles as sent: {str(e)}")
        return {"status": "error", "message": str(e), "updated_count": 0}
