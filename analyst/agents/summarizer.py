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

        # Calculate date range (last N weeks) - ensure we're using UTC timezone
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(weeks=weeks_back)
        
        # Log the exact date objects for debugging
        logger.info(f"Using start_date: {start_date} ({type(start_date)}), end_date: {end_date} ({type(end_date)})")
        
        # If the dates in MongoDB have timezone info, we should make our comparison dates timezone-aware
        try:
            import pytz
            # Create timezone-aware versions of our dates
            utc_tz = pytz.UTC
            start_date_tz = pytz.utc.localize(start_date) if start_date.tzinfo is None else start_date
            end_date_tz = pytz.utc.localize(end_date) if end_date.tzinfo is None else end_date
            
            # Use these timezone-aware dates instead
            start_date = start_date_tz
            end_date = end_date_tz
            
            logger.info(f"Adjusted to timezone-aware dates: start_date: {start_date}, end_date: {end_date}")
        except ImportError:
            logger.warning("pytz not available, continuing with naive datetimes")
        except Exception as e:
            logger.warning(f"Error adjusting timezones: {str(e)}, continuing with original dates")

        logger.info(
            f"Generating weekly summary for articles from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        )
        
        # Check for articles without dates (this may be a source of the problem)
        no_date_count = collection.count_documents({"article_date": {"$exists": False}})
        null_date_count = collection.count_documents({"article_date": None})
        logger.info(f"Articles with no article_date field: {no_date_count}")
        logger.info(f"Articles with null article_date: {null_date_count}")
        
        # Check article statuses
        status_counts = {}
        for status_type in ["PENDING", "APPROVED", "SENT", "DISCARDED"]:
            count = collection.count_documents({"status": status_type})
            status_counts[status_type] = count
        logger.info(f"Article status counts: {status_counts}")

        # Query for articles from the last N weeks with Italian content
        query = {
            "$and": [
                # Must have Italian content
                {"title_it": {"$exists": True, "$ne": None, "$ne": ""}},
                {"content_it": {"$exists": True, "$ne": None, "$ne": ""}},
                # Must be from the specified date range
                {"article_date": {"$gte": start_date, "$lte": end_date}},
                # Must be validated/approved articles
                {"status": {"$in": ["APPROVED", "SENT"]}},
            ]
        }
        
        # Log the exact query for debugging
        logger.info(f"MongoDB query: {query}")
        
        # As a test, try running just the date part of the query to see if we get any results
        date_only_query = {"article_date": {"$gte": start_date, "$lte": end_date}}
        date_only_count = collection.count_documents(date_only_query)
        logger.info(f"Articles in date range (any status/content): {date_only_count}")
        
        # Check if there are ANY articles with dates in the system
        any_date_count = collection.count_documents({"article_date": {"$exists": True, "$ne": None}})
        logger.info(f"Total articles with valid dates: {any_date_count}")
        
        # Check a wider date range to see if there might be a date format issue
        wider_start = end_date - timedelta(weeks=12)  # 3 months back
        wider_query = {"article_date": {"$gte": wider_start, "$lte": end_date}}
        wider_count = collection.count_documents(wider_query)
        logger.info(f"Articles in wider 3-month range: {wider_count}")
        
        # Test with exact date from the database
        # Try a direct lookup with a sample date format from the database
        try:
            from dateutil import parser
            
            # Parse a sample date in the format we've seen
            sample_date_str = "2025-10-21T09:14:00.000+00:00"  # Format seen in the database
            sample_date = parser.parse(sample_date_str)
            logger.info(f"Sample date parsed as: {sample_date} ({type(sample_date)})")
            
            # Try a query with this exact date format
            recent_date = datetime.utcnow() - timedelta(days=2)  # 2 days ago
            test_query = {"article_date": {"$gte": recent_date}}
            test_count = collection.count_documents(test_query)
            logger.info(f"Articles in the last 2 days: {test_count}")
        except Exception as e:
            logger.warning(f"Error during date format testing: {str(e)}")

        # Get articles
        articles = list(collection.find(query).sort("article_date", -1))
        
        # Add more detailed logging
        logger.info(f"Found {len(articles)} articles for summary generation")
        logger.info(f"Date range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # Log article dates for debugging
        if articles:
            oldest_date = min([a.get('article_date') for a in articles if a.get('article_date')])  
            newest_date = max([a.get('article_date') for a in articles if a.get('article_date')])
            logger.info(f"Oldest article date: {oldest_date}")
            logger.info(f"Newest article date: {newest_date}")
            
            # Check date distribution 
            date_counts = {}
            for article in articles:
                article_date = article.get('article_date')
                if article_date:
                    date_str = article_date.strftime('%Y-%m-%d')
                    date_counts[date_str] = date_counts.get(date_str, 0) + 1
            logger.info(f"Article date distribution: {date_counts}")

        # If not enough articles found, try with a wider date range
        if len(articles) < 5:
            logger.warning(f"Only {len(articles)} articles found in {weeks_back} weeks - trying wider range")
            
            # Double the date range
            extended_start = end_date - timedelta(weeks=weeks_back * 2)
            extended_query = query.copy()
            extended_query["$and"][2] = {"article_date": {"$gte": extended_start, "$lte": end_date}}
            
            logger.info(f"Extended date range to {extended_start.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Try with extended date range
            extended_articles = list(collection.find(extended_query).sort("article_date", -1))
            logger.info(f"Found {len(extended_articles)} articles with extended date range")
            
            # Use the extended articles if we found more
            if len(extended_articles) > len(articles):
                articles = extended_articles
                logger.info(f"Using extended date range with {len(articles)} articles")
                
            # Try even wider if still not enough
            if len(articles) < 5:
                logger.warning(f"Still only {len(articles)} articles - trying maximum range of 3 months")
                max_start = end_date - timedelta(weeks=12)  # 3 months
                max_query = query.copy()
                max_query["$and"][2] = {"article_date": {"$gte": max_start, "$lte": end_date}}
                
                max_articles = list(collection.find(max_query).sort("article_date", -1))
                logger.info(f"Found {len(max_articles)} articles with maximum 3-month range")
                
                if len(max_articles) > len(articles):
                    articles = max_articles
                    logger.info(f"Using maximum date range with {len(articles)} articles")            
        
        if len(articles) == 0:
            return {
                "status": "success",
                "message": "No articles found for the specified period",
                "articles_analyzed": 0,
                "summary_generated": False,
            }

        if len(articles) < 5:
            logger.warning(
                f"Only {len(articles)} articles found - summary may be limited"
            )

        # Generate the weekly summary
        logger.info("Generating weekly summary...")
        summary_result = generate_weekly_summary(articles, wait_time=10)

        if summary_result["generation_success"]:
            # Save summary to a separate collection
            summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][
                "weekly_summaries"
            ]

            # Find actual date range of included articles
            if articles:
                actual_dates = [a.get('article_date') for a in articles if a.get('article_date')]
                if actual_dates:
                    actual_start = min(actual_dates)
                    actual_end = max(actual_dates)
                    logger.info(f"Actual article date range: {actual_start.strftime('%Y-%m-%d')} to {actual_end.strftime('%Y-%m-%d')}")
                else:
                    actual_start = start_date
                    actual_end = end_date
            else:
                actual_start = start_date
                actual_end = end_date
                
            # Calculate actual weeks covered
            if actual_start and actual_end:
                actual_weeks = (actual_end - actual_start).days / 7
                actual_weeks = round(actual_weeks, 1)
            else:
                actual_weeks = weeks_back
                
            summary_doc = {
                "title": summary_result["title"],
                "executive_summary": summary_result["executive_summary"],
                "main_trends": summary_result["main_trends"],
                "featured_sectors": summary_result["featured_sectors"],
                "opportunities_italy": summary_result["opportunities_italy"],
                "full_content": summary_result["full_content"],
                "period_start": actual_start,
                "period_end": actual_end,
                "articles_analyzed": summary_result["articles_analyzed"],
                "llm_model": summary_result["llm_model"],
                "generated_at": summary_result["generated_at"],
                "weeks_analyzed": actual_weeks,
                "original_weeks_requested": weeks_back,
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
                "executive_summary": summary_result["executive_summary"][:200] + "..."
                if len(summary_result["executive_summary"]) > 200
                else summary_result["executive_summary"],
            }
        else:
            logger.error(
                f"Failed to generate summary: {summary_result.get('generation_error', 'Unknown error')}"
            )
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
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][
            "weekly_summaries"
        ]

        # Get the most recent summary
        latest_summary = summaries_collection.find_one({}, sort=[("generated_at", -1)])

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
        summaries_collection = client[getattr(settings, "MONGO_DB", "analyst")][
            "weekly_summaries"
        ]

        # Get recent summaries
        summaries = list(
            summaries_collection.find({}, sort=[("generated_at", -1)]).limit(limit)
        )

        return summaries

    except Exception as e:
        logger.error(f"Error retrieving summaries: {str(e)}")
        return []
    finally:
        if client:
            client.close()
