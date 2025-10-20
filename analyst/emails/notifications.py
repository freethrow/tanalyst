import os
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import resend
from articles.models import Article

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Resend API key
RESEND_API_KEY = settings.RESEND_API_KEY
if RESEND_API_KEY:
    logger.info("Initializing Resend with API key")
    resend.api_key = RESEND_API_KEY
    # Test if the API key appears valid (just checking format)
    if RESEND_API_KEY.startswith('re_') and len(RESEND_API_KEY) > 20:
        logger.info("Resend API key format appears valid")
    else:
        logger.warning("Resend API key format may be invalid - doesn't start with 're_' or is too short")
else:
    logger.error("RESEND_API_KEY not set in environment variables or settings")

# Email configuration


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
    try:
        # Validate Resend API key
        if not RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is not configured")

        # Fetch articles using Django ORM
        logger.info(f"Fetching {num_articles} latest validated unused articles")

        # Debug: Check total articles
        total_articles = Article.objects.count()
        logger.info(f"Total articles in database: {total_articles}")

        # Debug: Check articles with Italian content
        italian_articles = (
            Article.objects.filter(title_it__isnull=False, content_it__isnull=False)
            .exclude(title_it__exact="", content_it__exact="")
            .count()
        )
        logger.info(f"Articles with Italian content: {italian_articles}")

        # Debug: Check status field values
        pending_count = Article.objects.filter(status=Article.PENDING).count()
        approved_count = Article.objects.filter(status=Article.APPROVED).count()
        discarded_count = Article.objects.filter(status=Article.DISCARDED).count()
        sent_count = Article.objects.filter(status=Article.SENT).count()

        logger.info(
            f"Articles by status - Pending: {pending_count}, Approved: {approved_count}, Discarded: {discarded_count}, Sent: {sent_count}"
        )

        # Debug: Check how many approved articles have Italian content
        matching_count = (
            Article.objects.filter(
                status=Article.APPROVED,
                title_it__isnull=False,
                content_it__isnull=False,
            )
            .exclude(title_it__exact="", content_it__exact="")
            .count()
        )
        logger.info(f"Approved articles with Italian content: {matching_count}")

        # Get approved articles that haven't been sent yet
        articles_queryset = (
            Article.objects.filter(
                status=Article.APPROVED,
                title_it__isnull=False,
                content_it__isnull=False,
            )
            .exclude(title_it__exact="", content_it__exact="")
            .order_by("-time_translated")[:num_articles]
        )

        articles = list(articles_queryset)
        logger.info(f"Found {len(articles)} articles to include in email")

        # Debug: Show article details
        if articles:
            for i, article in enumerate(articles[:3]):  # Show first 3 articles
                logger.info(
                    f"Article {i + 1}: ID={article.id}, status={article.status}, title={article.title_it[:50] if article.title_it else 'None'}..."
                )

        # Mark the selected articles as sent
        if articles:
            article_ids = [article.id for article in articles]
            logger.info(f"About to update {len(article_ids)} articles: {article_ids}")

            # Check current state before update
            before_update = Article.objects.filter(id__in=article_ids).values_list(
                "id", "status"
            )
            logger.info(
                f"Before update - articles and their status: {list(before_update)}"
            )

            updated_count = Article.objects.filter(id__in=article_ids).update(
                status=Article.SENT
            )
            logger.info(f"Updated {updated_count} articles to SENT status")

            # Check state after update
            after_update = Article.objects.filter(id__in=article_ids).values_list(
                "id", "status"
            )
            logger.info(
                f"After update - articles and their status: {list(after_update)}"
            )
        else:
            logger.warning("No articles found matching criteria - email will be empty")

        # Check if we have articles to send
        if not articles:
            logger.warning("No articles found - not sending email")
            return {
                "status": "skipped",
                "recipient": recipient_email,
                "reason": "No approved articles found",
                "articles_sent": 0,
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Articles are already Django model instances, no processing needed
        # The template can access fields directly like {{ article.title_it }}

        # Prepare template context
        context = {
            "articles": articles,
            "article_count": len(articles),
            "recipient_email": recipient_email,
            "current_date": datetime.now(),
            "year": datetime.now().year,
        }

        logger.info(f"Template context prepared with {len(articles)} articles")

        # Render the HTML template
        logger.info("Rendering email template")
        try:
            html_content = render_to_string("email.html", context)
            logger.info(
                f"Template rendered successfully, content length: {len(html_content)}"
            )
        except Exception as template_error:
            logger.error(f"Template rendering failed: {template_error}")
            raise

        # Create plain text version
        text_content = strip_tags(html_content)

        # Prepare email parameters
        default_sender_email = sender_email or os.getenv("DEFAULT_FROM_EMAIL", "onboarding@resend.dev")
        default_sender_name = sender_name or os.getenv("DEFAULT_FROM_NAME", "Marko")
        
        # Log sender info for troubleshooting
        logger.info(f"Using sender: {default_sender_name} <{default_sender_email}>")

        # Generate default subject if not provided
        if not subject:
            subject = f"Le tue {len(articles)} notizie di business - {datetime.now().strftime('%d %B %Y')}"

        # Prepare Resend email parameters
        email_params = {
            "from": f"{default_sender_name} <{default_sender_email}>",
            "to": [recipient_email],
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "tags": [
                {"name": "type", "value": "latest_articles"},
                {"name": "article_count", "value": str(len(articles))},
            ],
        }

        # Send email via Resend
        logger.info(f"Sending email to {recipient_email}")
        try:
            email_result = resend.Emails.send(email_params)
            logger.info(f"✅ Email sent successfully. ID: {email_result.get('id')}")
        except Exception as resend_error:
            logger.error(f"Resend API error: {str(resend_error)}")
            # Log the response details if available
            if hasattr(resend_error, 'response') and resend_error.response:
                logger.error(f"Response: {resend_error.response.text}")
            raise

        # Return success result
        return {
            "status": "success",
            "email_id": email_result.get("id"),
            "recipient": recipient_email,
            "subject": subject,
            "articles_sent": len(articles),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to send email to {recipient_email}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error details: {repr(e)}")
        
        # Check if there are issues with the template data
        if articles and 'template' in str(e).lower():
            try:
                # Log info about articles that might cause template issues
                logger.error("Possible template data issue, checking articles:")
                for idx, article in enumerate(articles[:3]):
                    logger.error(f"Article {idx}: title_it={bool(article.title_it)}, content_it={bool(article.content_it)}, ")
                    logger.error(f"          has url: {hasattr(article, 'url') and bool(article.url)}")
            except Exception as article_error:
                logger.error(f"Error checking articles: {article_error}")

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

    except Exception as e:
        logger.error(f"Unexpected error in email task: {e}")
        return {
            "status": "failed",
            "recipient": recipient_email,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
