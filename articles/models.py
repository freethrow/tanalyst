from django.db import models

from django.utils import timezone

from django_mongodb_backend.managers import MongoManager


class Article(models.Model):
    """
    Article model for storing multilingual article content
    with tracking for validation and usage status.
    Compatible with MongoDB Compass document structure.
    """
    
    # Status constants
    PENDING = 'PENDING'
    APPROVED = 'APPROVED'
    DISCARDED = 'DISCARDED'
    SENT = 'SENT'
    
    STATUS_CHOICES = [
        (PENDING, 'Pending Review'),
        (APPROVED, 'Approved'),
        (DISCARDED, 'Discarded'),
        (SENT, 'Sent in Email'),
    ]

    # Title fields - matching MongoDB field names exactly
    title_en = models.CharField(
        max_length=500,
        db_column="title_en",  # Explicitly set column name
        help_text="Article title in English",
    )

    title_it = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_column="title_it",  # Explicitly set column name
        help_text="Article title in Italian",
    )

    title_rs = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        db_column="title_rs",  # Explicitly set column name
        help_text="Article title in Serbian",
    )

    # Date when the article was scraped
    scraped_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column="scraped_date",
        help_text="Date and time when the article was scraped",
    )

    # LLM model used for translation
    llm_model = models.CharField(
        null=True,
        blank=True,
        db_column="llm_model",
        help_text="LLM model used for translation",
        max_length=100,
    )

    # Content in English and Italian
    content_en = models.TextField(
        db_column="content_en", help_text="Full article content in English"
    )

    content_it = models.TextField(
        null=True,
        blank=True,
        db_column="content_it",
        help_text="Full article content in Italian",
    )

    content_rs = models.TextField(
        null=True,
        blank=True,
        db_column="content_rs",
        help_text="Full article content in Serbian",
    )

    sector = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_column="sector",
        help_text="Sector of the article",
    )

    # Original article publication date
    article_date = models.DateTimeField(
        null=True,
        blank=True,
        db_column="article_date",
        help_text="Original publication date of the article",
    )

    # URL field
    url = models.URLField(
        blank=True, null=True, db_column="url", help_text="Original article URL"
    )

    # Source field
    source = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        db_column="source",
        help_text="The source of the article",
    )

    # Status field replacing validated and used
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING,
        db_column="status",
        help_text="Current status of the article in the workflow"
    )

    time_translated = models.DateTimeField(
        null=True,
        blank=True,
        db_column="time_translated",
        help_text="Date and time when the article was translated",
    )

    # Custom manager for MongoDB
    # https://django-mongodb-backend.readthedocs.io/en/latest/ref/models/querysets/
    objects = MongoManager()

    class Meta:
        # MongoDB collection name
        db_table = "articles"

        # Set to False since we're managing the collection through MongoDB Compass
        managed = False

        # Indexes for better query performance
        indexes = [
            models.Index(fields=["scraped_date"]),
            models.Index(fields=["article_date"]),
            models.Index(fields=["status"]),
        ]

        # Default ordering
        ordering = ["-scraped_date"]

        # Verbose names for admin interface
        verbose_name = "Article"
        verbose_name_plural = "Articles"

    def __str__(self):
        """
        String representation of the Article model.
        Returns the English title if available, otherwise Italian.
        """
        return (
            f"{self.llm_model}: {self.title_en}"
            if self.title_en
            else self.title_it or "Untitled Article"
        )

    def is_approved(self):
        """
        Helper method to check if article is approved.
        """
        return self.status == self.APPROVED

    def is_sent(self):
        """
        Helper method to check if article has been sent.
        """
        return self.status == self.SENT

    def is_pending(self):
        """
        Helper method to check if article is pending review.
        """
        return self.status == self.PENDING

    def is_discarded(self):
        """
        Helper method to check if article is discarded.
        """
        return self.status == self.DISCARDED

    def mark_as_approved(self):
        """
        Helper method to mark the article as approved.
        """
        self.status = self.APPROVED
        self.save(update_fields=["status"])

    def mark_as_sent(self):
        """
        Helper method to mark the article as sent.
        """
        self.status = self.SENT
        self.save(update_fields=["status"])

    def mark_as_discarded(self):
        """
        Helper method to mark the article as discarded.
        """
        self.status = self.DISCARDED
        self.save(update_fields=["status"])

    def mark_as_pending(self):
        """
        Helper method to mark the article as pending.
        """
        self.status = self.PENDING
        self.save(update_fields=["status"])

    def get_content_by_language(self, language="en"):
        """
        Helper method to get content based on language preference.


        Args:
            language (str): Language code ('en' for English, 'it' for Italian)


        Returns:
            str: Article content in the requested language
        """
        if language == "it":
            return self.content_it
        return self.content_en

    def get_title_by_language(self, language="en"):
        """
        Helper method to get title based on language preference.


        Args:
            language (str): Language code ('en' for English, 'it' for Italian)


        Returns:
            str: Article title in the requested language
        """
        if language == "it":
            return self.title_it
        return self.title_en

    @property
    def has_italian_translation(self):
        """
        Check if Italian translation exists.
        """
        return bool(self.title_it and self.content_it)

    @property
    def days_since_scraped(self):
        """
        Calculate days since the article was scraped.
        """
        if self.scraped_date:
            delta = timezone.now() - self.scraped_date
            return delta.days
        return None

    def to_dict(self):
        """
        Convert model instance to dictionary format similar to MongoDB document.
        Useful for debugging or data export.
        """
        return {
            "_id": str(self.id) if self.id else None,
            "title_en": self.title_en,
            "title_it": self.title_it,
            "article_date": self.article_date.isoformat()
            if self.article_date
            else None,
            "content_en": self.content_en,
            "content_it": self.content_it,
            "url": self.url,
            "source": self.source,
            "scraped_date": self.scraped_date.isoformat()
            if self.scraped_date
            else None,
            "llm_model": self.llm_model,
            "status": self.status,
        }
