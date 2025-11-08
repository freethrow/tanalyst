import os
import logging
import io
import base64
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from celery import shared_task
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.contrib.auth.models import User
import resend
from articles.models import Article
from articles.weasyprint_generators import ArticlesPDFGenerator

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
    recipient_email: Optional[str] = None,
    subject: Optional[str] = None,
    num_articles: int = 10,
    sender_email: Optional[str] = None,
    sender_name: Optional[str] = None,
    send_to_all_users: bool = False
) -> Dict[str, Any]:
    """
    Send an email with the latest articles to recipients, including PDF attachments.

    Args:
        recipient_email: The email address to send to (ignored if send_to_all_users is True)
        subject: Email subject (optional, will use default if not provided)
        num_articles: Number of latest articles to include (default: 10)
        sender_email: Sender email address (optional, uses env variable if not provided)
        sender_name: Sender name (optional, uses env variable if not provided)
        send_to_all_users: If True, send to all users with email addresses (default: False)

    Returns:
        Dict with status and details of the email sending operation
    """
    try:
        # Validate Resend API key
        if not RESEND_API_KEY:
            raise ValueError("RESEND_API_KEY is not configured")
            
        # Determine recipients
        recipients = []
        if send_to_all_users:
            # Get all users with valid email addresses
            users = User.objects.exclude(email__isnull=True).exclude(email="")
            recipients = [user.email for user in users]
            logger.info(f"Found {len(recipients)} users with email addresses")
        elif recipient_email:
            recipients = [recipient_email]
        else:
            raise ValueError("Either recipient_email or send_to_all_users must be specified")
        
        if not recipients:
            logger.warning("No recipients found to send email to")
            return {
                "status": "skipped",
                "reason": "No recipients found",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Fetch articles using Django ORM
        logger.info(f"Fetching {num_articles} latest validated unused articles")

        # Debug: Check total articles
        total_articles = Article.objects.count()
        logger.info(f"Total articles in database: {total_articles}")

        # Debug: Check articles with Italian content
        italian_articles = Article.objects.with_italian_translations().count()
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
            Article.objects.with_italian_translations()
            .filter(status=Article.APPROVED)
            .count()
        )
        logger.info(f"Approved articles with Italian content: {matching_count}")

        # Get approved articles that haven't been sent yet
        articles_queryset = (
            Article.objects.with_italian_translations()
            .filter(status=Article.APPROVED)
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
                "recipients": recipients,
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
            "recipient_emails": recipients,
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
        default_sender_email = sender_email or os.getenv("DEFAULT_FROM_EMAIL", "tradeAInalist@itabeograd.rs")
        default_sender_name = sender_name or os.getenv("DEFAULT_FROM_NAME", "Trade AI Analyst")
        
        # Log sender info for troubleshooting
        logger.info(f"Using sender: {default_sender_name} <{default_sender_email}>")

        # Generate default subject if not provided
        if not subject:
            subject = f"Le tue {len(articles)} notizie di business - {datetime.now().strftime('%d %B %Y')}"
            
        # Generate PDF attachment
        logger.info("Generating PDF attachment of articles")
        pdf_buffer = io.BytesIO()
        try:
            pdf_generator = ArticlesPDFGenerator()
            # Convert the article query set to a list for the PDF generator
            pdf_content = pdf_generator.generate_articles_pdf_bytes(articles)
            pdf_buffer.write(pdf_content)
            pdf_buffer.seek(0)
            logger.info(f"PDF generated successfully, size: {len(pdf_content)} bytes")
            has_attachment = True
        except Exception as pdf_error:
            logger.error(f"Failed to generate PDF: {str(pdf_error)}")
            pdf_buffer = None
            has_attachment = False

        # Prepare Resend email parameters
        email_params = {
            "from": f"{default_sender_name} <{default_sender_email}>",
            "to": recipients,
            "subject": subject,
            "html": html_content,
            "text": text_content,
            "tags": [
                {"name": "type", "value": "latest_articles"},
                {"name": "article_count", "value": str(len(articles))},
            ],
        }
        
        # Add PDF attachment if available
        if has_attachment and pdf_buffer:
            attachment_filename = f"articoli_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            # Base64 encode the PDF content for JSON serialization
            pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            
            email_params["attachments"] = [
                {
                    "filename": attachment_filename,
                    "content": pdf_base64,
                    "content_type": "application/pdf",
                }
            ]

        # Send email via Resend
        logger.info(f"Sending email to {len(recipients)} recipients")
        try:
            email_result = resend.Emails.send(email_params)
            logger.info(f"✅ Email sent successfully. ID: {email_result.get('id')}")
            if pdf_buffer:
                pdf_buffer.close()
        except Exception as resend_error:
            logger.error(f"Resend API error: {str(resend_error)}")
            # Log the response details if available
            if hasattr(resend_error, 'response') and resend_error.response:
                logger.error(f"Response: {resend_error.response.text}")
            if pdf_buffer:
                pdf_buffer.close()
            raise

        # Return success result
        return {
            "status": "success",
            "email_id": email_result.get("id"),
            "recipients": recipients,
            "recipient_count": len(recipients),
            "subject": subject,
            "articles_sent": len(articles),
            "has_attachment": has_attachment,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ Failed to send email to {len(recipients) if recipients else 'recipients'}: {str(e)}")
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
            "recipients": recipients,
            "recipient_count": len(recipients) if recipients else 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Unexpected error in email task: {e}")
        return {
            "status": "failed",
            "recipients": recipients if 'recipients' in locals() else [],
            "recipient_count": len(recipients) if 'recipients' in locals() and recipients else 0,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat(),
        }
