"""
One-off script to clean up articles collection:
1. Remove scraped_date field from any document if it exists
2. Set status to "PENDING" for all documents that don't have a status
"""

from django.core.management.base import BaseCommand
from pymongo import MongoClient
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Clean up articles collection: remove scraped_date field and set default status'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without actually modifying the database',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Get MongoDB connection
        mongo_uri = getattr(
            settings,
            "MONGO_URI",
            os.getenv("MONGO_URI", "mongodb://localhost:8818/?directConnection=true"),
        )
        mongo_db = getattr(settings, "MONGO_DB", os.getenv("MONGO_DB", "analyst"))
        
        client = MongoClient(mongo_uri)
        db = client[mongo_db]
        collection = db["articles"]
        
        self.stdout.write(
            self.style.SUCCESS(f"Connected to MongoDB: {mongo_db}.articles")
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY RUN MODE - No changes will be made")
            )
        
        # Task 1: Remove scraped_date field
        self.stdout.write("\n" + "="*50)
        self.stdout.write("TASK 1: Remove scraped_date field")
        self.stdout.write("="*50)
        
        # Find documents with scraped_date field
        docs_with_scraped_date = collection.count_documents({"scraped_date": {"$exists": True}})
        self.stdout.write(f"Found {docs_with_scraped_date} documents with 'scraped_date' field")
        
        if docs_with_scraped_date > 0:
            if not dry_run:
                # Remove scraped_date field from all documents
                result = collection.update_many(
                    {"scraped_date": {"$exists": True}},
                    {"$unset": {"scraped_date": ""}}
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Removed 'scraped_date' field from {result.modified_count} documents")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Would remove 'scraped_date' field from {docs_with_scraped_date} documents")
                )
        else:
            self.stdout.write(self.style.SUCCESS("✅ No documents found with 'scraped_date' field"))
        
        # Task 2: Set status to PENDING for documents without status
        self.stdout.write("\n" + "="*50)
        self.stdout.write("TASK 2: Set default status to PENDING")
        self.stdout.write("="*50)
        
        # Find documents without status or with null/empty status
        docs_without_status = collection.count_documents({
            "$or": [
                {"status": {"$exists": False}},
                {"status": None},
                {"status": ""}
            ]
        })
        self.stdout.write(f"Found {docs_without_status} documents without status")
        
        if docs_without_status > 0:
            if not dry_run:
                # Set status to PENDING for documents without status
                result = collection.update_many(
                    {
                        "$or": [
                            {"status": {"$exists": False}},
                            {"status": None},
                            {"status": ""}
                        ]
                    },
                    {"$set": {"status": "PENDING"}}
                )
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Set status to 'PENDING' for {result.modified_count} documents")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"Would set status to 'PENDING' for {docs_without_status} documents")
                )
        else:
            self.stdout.write(self.style.SUCCESS("✅ All documents already have a status"))
        
        # Summary
        self.stdout.write("\n" + "="*50)
        self.stdout.write("SUMMARY")
        self.stdout.write("="*50)
        
        # Get final counts
        total_docs = collection.count_documents({})
        docs_with_status = collection.count_documents({"status": {"$exists": True, "$ne": None, "$ne": ""}})
        remaining_scraped_date = collection.count_documents({"scraped_date": {"$exists": True}})
        
        self.stdout.write(f"Total documents in collection: {total_docs}")
        self.stdout.write(f"Documents with status: {docs_with_status}")
        self.stdout.write(f"Documents with scraped_date field: {remaining_scraped_date}")
        
        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Cleanup completed successfully!"))
        else:
            self.stdout.write(self.style.WARNING("\n🔍 Dry run completed. Run without --dry-run to apply changes."))
        
        # Show status distribution
        self.stdout.write("\nStatus distribution:")
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        status_counts = list(collection.aggregate(status_pipeline))
        for status_doc in status_counts:
            status = status_doc["_id"] or "null/empty"
            count = status_doc["count"]
            self.stdout.write(f"  {status}: {count}")
        
        client.close()
