# analyst/agents/summarizer.py
import asyncio
from datetime import datetime, timedelta
import os
from time import sleep
from typing import Dict, Any, List
import logging

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openrouter import OpenRouterProvider
from pydantic_ai import Agent
from pymongo import MongoClient
from celery import shared_task
from django.conf import settings


load_dotenv("../.env")

# Configure logging
logger = logging.getLogger(__name__)

# Model configuration
MODEL_NAME = os.getenv("LLM_MODEL")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
model = OpenAIChatModel(
    model_name=MODEL_NAME,
    provider=OpenRouterProvider(api_key=OPENROUTER_API_KEY),
)


class WeeklySummary(BaseModel):
    """Structured output for weekly business summary in Italian"""

    titolo: str = Field(description="Titolo del riassunto settimanale")
    riassunto_esecutivo: str = Field(
        description="Breve riassunto esecutivo (2-3 frasi) dei punti principali della settimana"
    )
    tendenze_principali: List[str] = Field(
        description="Lista delle 3-5 tendenze principali emerse durante la settimana"
    )
    settori_in_evidenza: List[str] = Field(
        description="Lista dei settori che hanno avuto maggiore rilevanza durante la settimana"
    )
    opportunita_per_italia: str = Field(
        description="Analisi delle opportunità per le aziende italiane basate sulle notizie della settimana"
    )
    contenuto_completo: str = Field(
        description="Riassunto completo e dettagliato della settimana in formato articolo"
    )


def get_system_prompt() -> str:
    """Get the system prompt for weekly summary generation."""
    return """You are an expert business analyst specializing in creating weekly summaries of business and economic news.

Your task is to analyze business articles from the past two weeks and create a comprehensive weekly summary in Italian.

ANALYSIS GUIDELINES:
- Focus on the most significant business trends and developments
- Identify patterns and connections between different news stories
- Highlight sectors that showed particular activity or growth
- Analyze market movements, investments, and business opportunities
- Consider geopolitical and economic factors affecting business
- Emphasize opportunities for Italian companies and investors

SUMMARY STRUCTURE:
1. Executive Summary: 2-3 sentences capturing the week's most important developments
2. Main Trends: 3-5 key trends that emerged from the news analysis
3. Featured Sectors: Sectors that were most prominent in the news
4. Opportunities for Italy: Specific opportunities for Italian businesses based on the week's news
5. Complete Content: A full article-style summary (300-500 words)

WRITING STYLE:
- Use professional Italian business language
- Write in a clear, engaging, and informative style
- Maintain objectivity while providing insightful analysis
- Use proper business terminology
- Structure content logically with smooth transitions
- Make it suitable for business executives and decision-makers

OUTPUT REQUIREMENTS:
- All content must be in Italian
- Provide actionable insights where possible
- Ensure the summary is comprehensive yet concise
- Focus on information that would be valuable for Italian business readers"""


def get_mongodb_connection():
    """Get MongoDB connection using settings from Django or environment variables."""
    mongo_uri = getattr(
        settings,
        "MONGO_URI",
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


async def generate_weekly_summary_async(
    articles: List[Dict[str, Any]], wait_time: int = 10
) -> Dict[str, Any]:
    """
    Generate a weekly summary from a list of articles.

    Args:
        articles: List of article dictionaries with Italian content
        wait_time: Seconds to wait before generation (rate limiting)

    Returns:
        Dict with generated summary and metadata
    """
    # Create the agent
    agent = Agent(
        model=model,
        output_type=WeeklySummary,
        system_prompt=get_system_prompt(),
    )

    # Prepare articles text for analysis
    articles_text = ""
    for i, article in enumerate(articles, 1):
        title = article.get("title_it", "Titolo non disponibile")
        content = article.get("content_it", "")
        sector = article.get("sector", "Non specificato")
        date = article.get("article_date", "")
        
        articles_text += f"""
Articolo {i}:
Titolo: {title}
Settore: {sector}
Data: {date}
Contenuto: {content[:500]}...

---
"""

    prompt = f"""Analizza le seguenti notizie di business degli ultimi due settimane e crea un riassunto settimanale completo.

Notizie da analizzare:
{articles_text}

Crea un riassunto settimanale professionale che evidenzi:
- Le tendenze principali emerse
- I settori più attivi
- Le opportunità per le aziende italiane
- Un'analisi complessiva del panorama business

Il riassunto deve essere informativo, ben strutturato e utile per dirigenti aziendali italiani."""

    # Wait for rate limiting
    if wait_time > 0:
        logger.info(f"Waiting {wait_time} seconds to avoid rate limits...")
        sleep(wait_time)

    try:
        result = await agent.run(prompt)
        summary = result.output

        return {
            "title": summary.titolo,
            "executive_summary": summary.riassunto_esecutivo,
            "main_trends": summary.tendenze_principali,
            "featured_sectors": summary.settori_in_evidenza,
            "opportunities_italy": summary.opportunita_per_italia,
            "full_content": summary.contenuto_completo,
            "llm_model": MODEL_NAME,
            "generated_at": datetime.utcnow(),
            "articles_analyzed": len(articles),
            "generation_success": True,
        }
    except Exception as e:
        logger.error(f"Summary generation error: {str(e)}")
        return {
            "title": None,
            "executive_summary": None,
            "main_trends": None,
            "featured_sectors": None,
            "opportunities_italy": None,
            "full_content": None,
            "llm_model": MODEL_NAME,
            "generated_at": datetime.utcnow(),
            "articles_analyzed": len(articles),
            "generation_success": False,
            "generation_error": str(e),
        }


def generate_weekly_summary(
    articles: List[Dict[str, Any]], wait_time: int = 10
) -> Dict[str, Any]:
    """
    Synchronous wrapper for generate_weekly_summary_async.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(
            generate_weekly_summary_async(articles, wait_time)
        )
    finally:
        loop.close()


@shared_task(bind=True, max_retries=3, name="generate_weekly_summary")
def generate_weekly_summary_task(self, weeks_back: int = 2):
    """
    Generate a weekly summary from articles of the last specified weeks.

    Args:
        weeks_back: Number of weeks back to analyze (default: 2)

    Returns:
        Dict with generation statistics and summary
    """
    client = None

    try:
        # Get MongoDB connection
        client, collection = get_mongodb_connection()

        # Calculate date range (last N weeks)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks_back)

        logger.info(f"Generating weekly summary for articles from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

        # Query for articles from the last N weeks with Italian content
        query = {
            "$and": [
                # Must have Italian content
                {"title_it": {"$exists": True, "$ne": None, "$ne": ""}},
                {"content_it": {"$exists": True, "$ne": None, "$ne": ""}},
                # Must be from the specified date range
                {"article_date": {"$gte": start_date, "$lte": end_date}},
                # Must be validated/approved articles
                {"status": {"$in": ["APPROVED", "SENT"]}}
            ]
        }

        # Get articles
        articles = list(collection.find(query).sort("article_date", -1))
        
        logger.info(f"Found {len(articles)} articles for summary generation")

        if len(articles) == 0:
            return {
                "status": "success",
                "message": "No articles found for the specified period",
                "articles_analyzed": 0,
                "summary_generated": False,
            }

        if len(articles) < 5:
            logger.warning(f"Only {len(articles)} articles found - summary may be limited")

        # Generate the weekly summary
        logger.info("Generating weekly summary...")
        summary_result = generate_weekly_summary(articles, wait_time=10)

        if summary_result["generation_success"]:
            # Save summary to a separate collection
            summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")]["weekly_summaries"]
            
            summary_doc = {
                "title": summary_result["title"],
                "executive_summary": summary_result["executive_summary"],
                "main_trends": summary_result["main_trends"],
                "featured_sectors": summary_result["featured_sectors"],
                "opportunities_italy": summary_result["opportunities_italy"],
                "full_content": summary_result["full_content"],
                "period_start": start_date,
                "period_end": end_date,
                "articles_analyzed": summary_result["articles_analyzed"],
                "llm_model": summary_result["llm_model"],
                "generated_at": summary_result["generated_at"],
                "weeks_analyzed": weeks_back,
            }
            
            # Insert the summary
            result = summaries_collection.insert_one(summary_doc)
            summary_id = result.inserted_id
            
            logger.info(f"✅ Weekly summary generated and saved with ID: {summary_id}")
            
            return {
                "status": "success",
                "message": "Weekly summary generated successfully",
                "summary_id": str(summary_id),
                "articles_analyzed": len(articles),
                "summary_generated": True,
                "title": summary_result["title"],
                "executive_summary": summary_result["executive_summary"][:200] + "..." if len(summary_result["executive_summary"]) > 200 else summary_result["executive_summary"],
            }
        else:
            logger.error(f"Failed to generate summary: {summary_result.get('generation_error', 'Unknown error')}")
            return {
                "status": "error",
                "message": f"Failed to generate summary: {summary_result.get('generation_error', 'Unknown error')}",
                "articles_analyzed": len(articles),
                "summary_generated": False,
            }

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        raise self.retry(exc=e, countdown=60 * (self.request.retries + 1))

    finally:
        if client:
            client.close()


def get_latest_weekly_summary():
    """
    Get the most recent weekly summary from the database.
    
    Returns:
        Dict with the latest summary or None if no summaries exist
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")]["weekly_summaries"]
        
        # Get the most recent summary
        latest_summary = summaries_collection.find_one(
            {},
            sort=[("generated_at", -1)]
        )
        
        return latest_summary
        
    except Exception as e:
        logger.error(f"Error retrieving latest summary: {str(e)}")
        return None
    finally:
        if client:
            client.close()


def get_weekly_summaries(limit: int = 10):
    """
    Get recent weekly summaries from the database.
    
    Args:
        limit: Maximum number of summaries to retrieve
        
    Returns:
        List of summary dictionaries
    """
    client = None
    try:
        client, _ = get_mongodb_connection()
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")]["weekly_summaries"]
        
        # Get recent summaries
        summaries = list(summaries_collection.find(
            {},
            sort=[("generated_at", -1)]
        ).limit(limit))
        
        return summaries
        
    except Exception as e:
        logger.error(f"Error retrieving summaries: {str(e)}")
        return []
    finally:
        if client:
            client.close()
