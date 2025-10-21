import os
import json
import logging
from django.core.management.base import BaseCommand
from articles.models import Article
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Export articles from MongoDB to a JSON file (without embeddings)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Path to output JSON file. Default: articles_export_YYYYMMDD.json in current directory'
        )
        parser.add_argument(
            '--status',
            type=str,
            default=None,
            help='Filter by status (PENDING, APPROVED, DISCARDED, SENT). Omit for all articles.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of articles to export. Default: no limit'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            default=False,
            help='Output pretty-printed JSON'
        )

    def handle(self, *args, **options):
        # Set up output file
        output_file = options['output']
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = f"articles_export_{timestamp}.json"
        
        # Build filter criteria
        filters = {}
        if options['status']:
            filters['status'] = options['status']
        
        # Query articles
        query = Article.objects.filter(**filters)
        if options['limit']:
            query = query[:options['limit']]
        
        # Count total
        total_articles = query.count()
        self.stdout.write(f"Exporting {total_articles} articles to {output_file}")
        
        # Process and export articles
        articles_data = []
        skipped_count = 0
        
        for article in query:
            # Convert article to dict but skip embedding-related fields
            article_dict = {}
            for field in article._meta.fields:
                field_name = field.name
                if field_name in ['id', '_id']:
                    article_dict['_id'] = str(getattr(article, field.name))
                # Skip embedding-related fields
                elif field_name not in ['embedding', 'embedding_model', 'embedding_created_at', 
                                       'embedding_dimensions', 'embedding_error', 'embedding_failed_at']:
                    article_dict[field_name] = getattr(article, field_name)
            
            # Handle dates (convert to ISO format)
            for field_name in ['scraped_at', 'article_date', 'time_translated']:
                if field_name in article_dict and article_dict[field_name]:
                    article_dict[field_name] = article_dict[field_name].isoformat()
            
            articles_data.append(article_dict)
            
            # Progress reporting
            if len(articles_data) % 100 == 0:
                self.stdout.write(f"Processed {len(articles_data)} articles...")
        
        # Write JSON to file
        indent = 2 if options['pretty'] else None
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=indent)
        
        self.stdout.write(self.style.SUCCESS(f"Successfully exported {len(articles_data)} articles to {output_file}"))
        if skipped_count > 0:
            self.stdout.write(f"Skipped {skipped_count} articles due to errors")
