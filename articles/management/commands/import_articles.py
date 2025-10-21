import os
import json
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from articles.models import Article
from django.utils import timezone
from datetime import datetime

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Import articles from JSON file, skipping duplicates based on URL'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_file',
            type=str,
            help='Path to input JSON file with articles data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Perform a dry run without actually importing data'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            default=False,
            help='Update existing articles if URL matches (default is to skip)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Batch size for bulk operations. Default: 100'
        )

    def handle(self, *args, **options):
        input_file = options['input_file']
        dry_run = options['dry_run']
        update_existing = options['update']
        batch_size = options['batch_size']
        
        if not os.path.exists(input_file):
            self.stderr.write(self.style.ERROR(f"File not found: {input_file}"))
            return
        
        # Read JSON file
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                articles_data = json.load(f)
        except json.JSONDecodeError:
            self.stderr.write(self.style.ERROR(f"Invalid JSON file: {input_file}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error reading file: {str(e)}"))
            return
        
        self.stdout.write(f"Found {len(articles_data)} articles in import file")
        
        # Collect all URLs from the import data for efficient checking
        urls = [article.get('url') for article in articles_data if article.get('url')]
        unique_urls = set(urls)
        
        # Check for duplicate URLs in input file
        if len(unique_urls) < len(urls):
            self.stdout.write(self.style.WARNING(
                f"Input file contains {len(urls) - len(unique_urls)} duplicate URLs"
            ))
        
        # Get existing URLs from database
        existing_articles = list(Article.objects.filter(url__in=list(unique_urls)))
        existing_urls = {article.url for article in existing_articles if article.url}
        
        self.stdout.write(f"Found {len(existing_urls)} already existing articles with matching URLs")
        
        # Initialize counters
        to_insert = []
        to_update = []
        skipped = 0
        inserted = 0
        updated = 0
        errors = 0
        
        # Process articles in batches
        batch_count = 0
        
        for article in articles_data:
            try:
                # Skip entries without URL
                if not article.get('url'):
                    skipped += 1
                    continue
                
                # Format dates properly
                for field in ['scraped_at', 'article_date', 'time_translated']:
                    if field in article and article[field] and isinstance(article[field], str):
                        try:
                            article[field] = datetime.fromisoformat(article[field])
                        except ValueError:
                            # Remove invalid date fields
                            article.pop(field, None)
                
                # Remove _id field if present to avoid conflicts
                article_id = article.pop('_id', None)
                
                # Check if URL already exists
                if article['url'] in existing_urls:
                    if update_existing:
                        # Add to update list
                        to_update.append(article)
                    else:
                        skipped += 1
                else:
                    # Add to insert list
                    to_insert.append(article)
            
            except Exception as e:
                self.stderr.write(f"Error processing article: {str(e)}")
                errors += 1
            
            # When batch size reached, process batch
            if len(to_insert) + len(to_update) >= batch_size:
                batch_count += 1
                if not dry_run:
                    with transaction.atomic():
                        # Handle inserts
                        if to_insert:
                            for article_data in to_insert:
                                try:
                                    Article.objects.create(**article_data)
                                except Exception as e:
                                    self.stderr.write(f"Insert error: {str(e)}")
                                    errors += 1
                                    continue
                            inserted += len(to_insert)
                        
                        # Handle updates
                        if to_update:
                            for article_data in to_update:
                                try:
                                    url = article_data.get('url')
                                    if url:
                                        Article.objects.filter(url=url).update(**article_data)
                                except Exception as e:
                                    self.stderr.write(f"Update error: {str(e)}")
                                    errors += 1
                                    continue
                            updated += len(to_update)
                else:
                    # Dry run - just count
                    inserted += len(to_insert)
                    updated += len(to_update)
                
                self.stdout.write(f"Batch {batch_count}: Processed {len(to_insert)} inserts and {len(to_update)} updates")
                to_insert = []
                to_update = []
        
        # Process remaining articles
        if to_insert or to_update:
            batch_count += 1
            if not dry_run:
                with transaction.atomic():
                    # Handle inserts
                    if to_insert:
                        for article_data in to_insert:
                            try:
                                Article.objects.create(**article_data)
                            except Exception as e:
                                self.stderr.write(f"Insert error: {str(e)}")
                                errors += 1
                                continue
                        inserted += len(to_insert)
                    
                    # Handle updates
                    if to_update:
                        for article_data in to_update:
                            try:
                                url = article_data.get('url')
                                if url:
                                    Article.objects.filter(url=url).update(**article_data)
                            except Exception as e:
                                self.stderr.write(f"Update error: {str(e)}")
                                errors += 1
                                continue
                        updated += len(to_update)
            else:
                # Dry run - just count
                inserted += len(to_insert)
                updated += len(to_update)
                
            self.stdout.write(f"Batch {batch_count}: Processed {len(to_insert)} inserts and {len(to_update)} updates")
        
        # Summary
        self.stdout.write("\n--- Import Summary ---")
        self.stdout.write(f"Total articles in file: {len(articles_data)}")
        self.stdout.write(f"Articles inserted: {inserted}")
        self.stdout.write(f"Articles updated: {updated}")
        self.stdout.write(f"Articles skipped: {skipped}")
        self.stdout.write(f"Errors: {errors}")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No actual changes were made to the database"))
        else:
            self.stdout.write(self.style.SUCCESS("Import completed successfully"))
