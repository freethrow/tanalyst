import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from pymongo import MongoClient
from django.conf import settings
import resend

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Resend API key
RESEND_API_KEY = settings.RESEND_API_KEY
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
else:
    logger.error("RESEND_API_KEY not set in environment variables")

# MongoDB configuration
MONGODB_URI = settings.MONGODB_URI
DB_NAME = settings.DB_NAME
COLLECTION_NAME = "articles"


@shared_task(bind=True, max_retries=3, name="send_latest_articles_email")
def send_latest_articles_email(
    self,
    recipient_email: str,
    subject: Optional[str] = None,
    num_articles: int = 10,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an email with the latest articles to a recipient.

    Args:
        recipient_email: The email address to send to
        subject: Email subject (optional, will use default if not provided)
        num_articles: Number of latest articles to include (default: 10)
        language: Language for articles - 'it' for Italian, 'en' for English (default: 'it')
        sender_email: Sender email address (optional, uses env variable if not provided)
        sender_name: Sender name (optional, uses env variable if not provided)

    Returns:
        Dict with status and details of the email sending operation
    """
    client = None

    try:
        # Validate Resend API key
        if not RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is not configured")

        # Connect to MongoDB
        logger.info(f"Connecting to MongoDB to fetch {num_articles} latest articles")
        client = MongoClient(MONGODB_URI)
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]

        # Fetch articles that have Italian translations
        query = {
            "title_it": {"$exists": True, "$ne": None, "$ne": ""},
            "content_it": {"$exists": True, "$ne": None, "$ne": ""},
        }
        sort_field = "time_translated"

        # Fetch the latest articles
        articles = list(
            collection.find(query)
            .sort(sort_field, -1)  # Sort by most recent
            .limit(num_articles)
        )

        logger.info(f"Found {len(articles)} articles to include in email")

        # Process articles for the template
        processed_articles = []
        for article in articles:
            processed_article = {
                "title": article.get("title_it", ""),
                "content": article.get("content_it", ""),
                "sector": article.get("sector", ""),
                "url": article.get("url", ""),
                "published_date": article.get("published_date"),
                "time_translated": article.get("time_translated"),
            }

            # Create a content preview (first 300 characters)
            if processed_article["content"]:
                processed_article["preview"] = (
                    processed_article["content"][:300] + "..."
                )
            else:
                processed_article["preview"] = ""

            processed_articles.append(processed_article)

        # Prepare template context
        context = {
            "articles": processed_articles,
            "article_count": len(processed_articles),
            "recipient_email": recipient_email,
            "current_date": datetime.now(),
            "year": datetime.now().year,
        }

        # Render the HTML template
        logger.info("Rendering email template")
        html_content = render_to_string("email.html", context)

        # Create plain text version
        text_content = strip_tags(html_content)

        # Prepare email parameters
        default_sender_email = "onboarding@resend.dev"
        default_sender_name = sender_name or os.getenv("DEFAULT_FROM_NAME", "Marko")

        # Generate default subject if not provided
        if not subject:
            subject = f"Le tue {len(processed_articles)} notizie di business - {datetime.now().strftime('%d %B %Y')}"

        # Prepare Resend email parameters
        email_params = {
            "from": f"{default_sender_name} <{default_sender_email}>",
            "to": [recipient_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "tags": [
                {"name": "type", "value": "latest_articles"},
                {"name": "article_count", "value": str(len(processed_articles))},
            ],
        }

        # Send email via Resend
        logger.info(f"Sending email to {recipient_email}")
        email_result = resend.Emails.send(email_params)

        logger.info(f"✅ Email sent successfully. ID: {email_result.get('id')}")

        # Return success result
        return {
            "status": "success",
            "email_id": email_result.get("id"),
            "recipient": recipient_email,
            "subject": subject,
            "articles_sent": len(processed_articles),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to send email to {recipient_email}: {str(e)}")

        # Retry with exponential backoff
        if self.request.retries < self.max_retries:
            retry_in = 60 * (2**self.request.retries)  # Exponential backoff
            logger.info(f"Retrying in {retry_in} seconds...")
            raise self.retry(exc=e, countdown=retry_in)

        # Return failure result after all retries exhausted
        return {
            "status": "failed",
            "recipient": recipient_email,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }

    finally:
        # Clean up MongoDB connection
        if client:
            client.close()
