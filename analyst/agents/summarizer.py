# analyst/agents/summarizer.py
"""
Unified Summary Generator for both Topic (Selection) and Weekly summaries.
Generates newspaper-style articles in Italian from business news.
"""
import asyncio
from datetime import datetime, timedelta
import os
from time import sleep
from typing import Dict, Any, List, Optional
import logging

from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai import Agent
from pymongo import MongoClient
from bson import ObjectId
from celery import shared_task
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = os.getenv("LLM_MODEL", "anthropic/claude-3.5-sonnet")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

model = OpenAIChatModel(
    model_name=MODEL_NAME,
    provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
)

# Collection name for all summaries
SUMMARIES_COLLECTION = "summaries"


def get_system_prompt() -> str:
    """
    Unified system prompt for generating newspaper-style business articles in Italian.
    Used for both topic summaries and weekly summaries.
    """
    return """Sei un giornalista economico esperto che scrive per un quotidiano italiano di business come Il Sole 24 Ore.

Il tuo compito è analizzare gli articoli forniti e scrivere un pezzo giornalistico professionale che sintetizza e analizza le notizie.

STILE DI SCRITTURA:
- Scrivi come un articolo di giornale economico italiano
- Usa paragrafi fluidi e narrativa continua
- NO liste, NO bullet points, NO struttura rigida con titoli di sezione
- Integra naturalmente i riferimenti agli articoli con i loro URL inline
- Organizza il contenuto per temi e tendenze, non per singoli articoli

STRUTTURA NARRATIVA:
1. Inizia con un'apertura forte che cattura l'essenza delle tendenze principali
2. Sviluppa i temi attraverso paragrafi che integrano informazioni da multiple fonti
3. Quando menzioni informazioni specifiche, cita la fonte con URL inline
4. Collega gli sviluppi tra diversi settori evidenziando pattern comuni
5. Concludi con prospettive e implicazioni per il mercato italiano

REQUISITI:
- Scrivi interamente in italiano professionale
- Usa un tono analitico ma scorrevole e coinvolgente
- Ogni articolo fonte deve essere citato almeno una volta nel testo
- Evidenzia opportunità concrete per le aziende italiane
- Lunghezza: 400-800 parole

OUTPUT:
Restituisci SOLO il testo dell'articolo, senza titoli di sezione o formattazione speciale."""


def get_mongodb_connection():
    """Get MongoDB connection using settings from Django or environment variables."""
    mongo_uri = getattr(
        settings,
        "MONGODB_URI",
        os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true"),
    )
    mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))
    mongo_collection = getattr(
        settings, "MONGO_COLLECTION", os.getenv("MONGO_COLLECTION", "articles")
    )

    client = MongoClient(mongo_uri)
    db = client[mongo_db]
    collection = db[mongo_collection]

    return client, collection


def prepare_articles_text(articles: List[Dict[str, Any]], base_url: str = "") -> str:
    """
    Prepare articles text for the AI prompt.
    
    Args:
        articles: List of article dictionaries
        base_url: Base URL for internal article links (e.g., "http://127.0.0.1:8000")
    
    Returns:
        Formatted string with all articles
    """
    articles_text = ""
    
    for i, article in enumerate(articles, 1):
        # Get article details
        title = article.get("title_it") or article.get("title_en") or article.get("title", "Titolo non disponibile")
        content = article.get("content_it") or article.get("content_en") or article.get("content", "")
        sector = article.get("sector", "Non specificato")
        date = article.get("article_date", "")
        source = article.get("source", "")
        
        # Format date if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        
        # Get article ID for internal URL
        article_id = str(article.get("_id", article.get("id", "")))
        internal_url = f"{base_url}/article/{article_id}" if article_id else article.get("url", "")
        
        articles_text += f"""
---
Articolo {i}:
Titolo: {title}
Settore: {sector}
Data: {date}
Fonte: {source}
URL: {internal_url}
Contenuto: {content[:1000]}...
"""
    
    return articles_text


async def generate_summary_async(
    articles: List[Dict[str, Any]],
    summary_type: str = "topic",
    custom_prompt: Optional[str] = None,
    base_url: str = "",
    wait_time: int = 5
) -> Dict[str, Any]:
    """
    Generate a summary from a list of articles.
    
    Args:
        articles: List of article dictionaries
        summary_type: "topic" for selection summaries, "weekly" for periodic summaries
        custom_prompt: Optional custom instructions to append
        base_url: Base URL for internal article links
        wait_time: Seconds to wait before generation (rate limiting)
    
    Returns:
        Dict with generated summary and metadata
    """
    # Create the agent with system prompt
    agent = Agent(
        model=model,
        system_prompt=get_system_prompt(),
    )
    
    # Prepare articles text
    articles_text = prepare_articles_text(articles, base_url)
    
    # Build the user prompt
    prompt = f"""Analizza i seguenti articoli di business e scrivi un articolo giornalistico professionale in italiano.

{articles_text}

"""
    
    if custom_prompt:
        prompt += f"\nIstruzioni aggiuntive: {custom_prompt}\n"
    
    prompt += "\nScrivi l'articolo:"
    
    # Wait for rate limiting
    if wait_time > 0:
        logger.info(f"Waiting {wait_time} seconds to avoid rate limits...")
        sleep(wait_time)
    
    try:
        result = await agent.run(prompt)
        content = result.output
        
        # Extract article IDs
        article_ids = [str(a.get("_id", a.get("id", ""))) for a in articles if a.get("_id") or a.get("id")]
        
        return {
            "content": content,
            "summary_type": summary_type,
            "article_ids": article_ids,
            "articles_count": len(articles),
            "llm_model": MODEL_NAME,
            "generated_at": datetime.utcnow(),
            "generation_success": True,
        }
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        return {
            "content": None,
            "summary_type": summary_type,
            "article_ids": [],
            "articles_count": len(articles),
            "llm_model": MODEL_NAME,
            "generated_at": datetime.utcnow(),
            "generation_success": False,
            "generation_error": str(e),
        }


def generate_summary(
    articles: List[Dict[str, Any]],
    summary_type: str = "topic",
    custom_prompt: Optional[str] = None,
    base_url: str = "",
    wait_time: int = 5
) -> Dict[str, Any]:
    """
    Synchronous wrapper for generate_summary_async.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            generate_summary_async(articles, summary_type, custom_prompt, base_url, wait_time)
        )
    finally:
        loop.close()


def save_summary(summary_data: Dict[str, Any], title: str) -> str:
    """
    Save a summary to the database.
    
    Args:
        summary_data: Dictionary with summary content and metadata
        title: Title for the summary
    
    Returns:
        String ID of the saved summary
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][SUMMARIES_COLLECTION]
        
        doc = {
            "title": title,
            "content": summary_data.get("content"),
            "summary_type": summary_data.get("summary_type", "topic"),
            "article_ids": summary_data.get("article_ids", []),
            "articles_count": summary_data.get("articles_count", 0),
            "llm_model": summary_data.get("llm_model"),
            "generated_at": summary_data.get("generated_at", datetime.utcnow()),
        }
        
        result = summaries_collection.insert_one(doc)
        logger.info(f"Summary saved with ID: {result.inserted_id}")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error saving summary: {str(e)}")
        raise
    finally:
        if client:
            client.close()


def get_summaries(limit: int = 20, summary_type: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get recent summaries from the database.
    
    Args:
        limit: Maximum number of summaries to retrieve
        summary_type: Filter by type ("topic" or "weekly"), None for all
    
    Returns:
        List of summary dictionaries
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][SUMMARIES_COLLECTION]
        
        query = {}
        if summary_type:
            query["summary_type"] = summary_type
        
        summaries = list(
            summaries_collection.find(query).sort("generated_at", -1).limit(limit)
        )
        
        # Convert _id to string id
        for summary in summaries:
            summary["id"] = str(summary["_id"])
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error retrieving summaries: {str(e)}")
        return []
    finally:
        if client:
            client.close()


def get_summary_by_id(summary_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific summary by ID.
    
    Args:
        summary_id: The summary's MongoDB ObjectId as string
    
    Returns:
        Summary dictionary or None if not found
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][SUMMARIES_COLLECTION]
        
        summary = summaries_collection.find_one({"_id": ObjectId(summary_id)})
        
        if summary:
            summary["id"] = str(summary["_id"])
        
        return summary
        
    except Exception as e:
        logger.error(f"Error retrieving summary: {str(e)}")
        return None
    finally:
        if client:
            client.close()


def delete_summary(summary_id: str) -> bool:
    """
    Delete a summary by ID.
    
    Args:
        summary_id: The summary's MongoDB ObjectId as string
    
    Returns:
        True if deleted, False otherwise
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][SUMMARIES_COLLECTION]
        
        result = summaries_collection.delete_one({"_id": ObjectId(summary_id)})
        return result.deleted_count > 0
        
    except Exception as e:
        logger.error(f"Error deleting summary: {str(e)}")
        return False
    finally:
        if client:
            client.close()


@shared_task(bind=True, max_retries=3, name="generate_weekly_summary")
def generate_weekly_summary_task(self, weeks_back: int = 2):
    """
    Celery task to generate a weekly summary from recent articles.
    
    Args:
        weeks_back: Number of weeks back to analyze (default: 2)
    
    Returns:
        Dict with generation statistics and summary ID
    """
    client = None
    
    try:
        client, collection = get_mongodb_connection()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks_back)
        
        logger.info(f"Generating weekly summary for {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Query for approved articles with Italian content
        query = {
            "$and": [
                {"title_it": {"$exists": True, "$ne": None, "$ne": ""}},
                {"content_it": {"$exists": True, "$ne": None, "$ne": ""}},
                {"article_date": {"$gte": start_date, "$lte": end_date}},
                {"status": {"$in": ["APPROVED", "SENT"]}},
            ]
        }
        
        articles = list(collection.find(query).sort("article_date", -1).limit(50))
        logger.info(f"Found {len(articles)} articles for summary")
        
        # Try wider range if not enough articles
        if len(articles) < 5:
            logger.warning(f"Only {len(articles)} articles found, trying 3-month range")
            extended_start = end_date - timedelta(weeks=12)
            query["$and"][2] = {"article_date": {"$gte": extended_start, "$lte": end_date}}
            articles = list(collection.find(query).sort("article_date", -1).limit(50))
            logger.info(f"Found {len(articles)} articles with extended range")
        
        if len(articles) == 0:
            return {
                "status": "success",
                "message": "No articles found for the specified period",
                "articles_analyzed": 0,
                "summary_generated": False,
            }
        
        # Generate summary
        summary_result = generate_summary(
            articles,
            summary_type="weekly",
            wait_time=10
        )
        
        if summary_result["generation_success"]:
            # Create title based on date range
            title = f"Rassegna Business {start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m/%Y')}"
            
            # Save to database
            summary_id = save_summary(summary_result, title)
            
            logger.info(f"Weekly summary saved with ID: {summary_id}")
            
            return {
                "status": "success",
                "message": "Weekly summary generated successfully",
                "summary_id": summary_id,
                "articles_analyzed": len(articles),
                "summary_generated": True,
                "title": title,
            }
        else:
            logger.error(f"Failed to generate summary: {summary_result.get('generation_error')}")
            return {
                "status": "error",
                "message": f"Failed to generate summary: {summary_result.get('generation_error')}",
                "articles_analyzed": len(articles),
                "summary_generated": False,
            }
    
    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))
    
    finally:
        if client:
            client.close()


# Legacy function aliases for backward compatibility
def get_weekly_summaries(limit: int = 20) -> List[Dict[str, Any]]:
    """Get all summaries (legacy function name)."""
    return get_summaries(limit=limit)


def get_latest_weekly_summary() -> Optional[Dict[str, Any]]:
    """Get the most recent summary (legacy function name)."""
    summaries = get_summaries(limit=1)
    return summaries[0] if summaries else None
