from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from articles.models import Article


class Command(BaseCommand):
    help = 'Mark articles older than 30 days as SENT (used in email)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days threshold (default: 30)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        days_threshold = options['days']
        dry_run = options['dry_run']
        
        # Calculate the cutoff date
        cutoff_date = timezone.now() - timedelta(days=days_threshold)
        
        self.stdout.write(
            self.style.WARNING(
                f'\nLooking for articles older than {days_threshold} days (before {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")})'
            )
        )
        
        # Find articles that are:
        # 1. Older than the threshold (based on article_date)
        # 2. Not already marked as SENT
        # 3. Have Italian content (to match the existing workflow)
        old_articles = Article.objects.filter(
            article_date__lt=cutoff_date,
            title_it__isnull=False,
            content_it__isnull=False
        ).exclude(
            status=Article.SENT
        ).exclude(
            title_it__exact="",
            content_it__exact=""
        )
        
        count = old_articles.count()
        
        if count == 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✓ No articles found older than {days_threshold} days that need to be marked as SENT.'
                )
            )
            return
        
        self.stdout.write(
            self.style.WARNING(f'\nFound {count} articles to mark as SENT:')
        )
        
        # Show sample of articles that will be updated
        for article in old_articles[:5]:
            article_date_str = article.article_date.strftime("%Y-%m-%d") if article.article_date else "No date"
            self.stdout.write(
                f'  - {article.title_it[:60]}... ({article_date_str})'
            )
        
        if count > 5:
            self.stdout.write(f'  ... and {count - 5} more')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n[DRY RUN] Would mark {count} articles as SENT (no changes made)'
                )
            )
            return
        
        # Update the articles
        updated_count = 0
        for article in old_articles:
            article.status = Article.SENT
            article.save()
            updated_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully marked {updated_count} articles as SENT'
            )
        )
