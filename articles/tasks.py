from celery.utils.log import get_task_logger
from celery import shared_task
from time import sleep
from django.conf import settings

import os

import voyageai
from datetime import datetime

from analyst.emails.notifications import send_latest_articles_email
from pymongo import MongoClient

EMBEDDING_BATCH_SIZE = 10


logger = get_task_logger(__name__)

voyage_client = voyageai.Client(api_key=settings.VOYAGEAI_API_KEY)


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
    send_latest_articles_email.delay(
        recipient_email="aleksendric@gmail.com", num_articles=12
    )
    return "Scraping Ekapija started"


@shared_task(bind=True, max_retries=3, name="create_all_embeddings")
def create_all_embeddings(
    self, batch_size: int = EMBEDDING_BATCH_SIZE, limit: int = None
):
    """
    Create embeddings for all articles that don't have them.

    Args:
        batch_size: Number of articles to process per Voyage API call
        limit: Maximum total number of articles to process

    Returns:
        Dict with processing statistics
    """
    client = None

    try:
        client, collection = get_mongodb_connection()

        # Count articles needing embeddings
        query = {
            "$and": [
                # Articles without embeddings
                {
                    "$or": [
                        {"embedding": {"$exists": False}},
                        {"embedding": None},
                        {"embedding": []},
                    ]
                },
                # Articles with English OR Serbian content
                {
                    "$or": [
                        {
                            "$and": [
                                {"title_en": {"$exists": True, "$ne": None, "$ne": ""}},
                                {"content_en": {"$exists": True, "$ne": None, "$ne": ""}}
                            ]
                        },
                        {
                            "$and": [
                                {"title_rs": {"$exists": True, "$ne": None, "$ne": ""}},
                                {"content_rs": {"$exists": True, "$ne": None, "$ne": ""}}
                            ]
                        }
                    ]
                }
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
        sleep(30)  # Brief pause before starting

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
                # Generate embeddings for batch
                sleep(30)
                logger.info(f"Creating embeddings for batch of {len(texts)} articles")

                result = voyage_client.embed(
                    texts, model="voyage-3.5-lite", input_type="document"
                )

                # Update each article with its embedding
                for idx, (article_id, embedding) in enumerate(
                    zip(article_ids, result.embeddings)
                ):
                    try:
                        collection.update_one(
                            {"_id": article_id},
                            {
                                "$set": {
                                    "embedding": embedding,
                                    "embedding_model": "voyage-3.5-lite",
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
                logger.error(f"Batch embedding failed: {str(e)}")
                failed += len(texts)

                # Mark all in batch as failed
                """ for article_id in article_ids:
                    collection.update_one(
                        {"_id": article_id},
                        {
                            "$set": {
                                "embedding_error": str(e),
                                "embedding_failed_at": datetime.utcnow(),
                            }
                        },
                    ) """

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
