#!/usr/bin/env python
"""
Migration script to convert old validated/used fields to new status field.

This script updates existing articles in MongoDB to use the new status field
instead of the old validated and used boolean fields.

Run this script after updating your models to use the status field.
"""

import os
import sys
import django
from datetime import datetime

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "analyst.settings")
django.setup()

from articles.models import Article


def migrate_article_status():
    """
    Migrate articles from validated/used fields to status field.

    Migration logic:
    - validated=True, used=True -> status='SENT'
    - validated=True, used=False -> status='APPROVED'
    - validated=False -> status='DISCARDED'
    - validated=None/False (not validated) -> status='PENDING'
    """

    print("🔄 Starting migration from validated/used fields to status field...")
    print(f"⏰ Migration started at: {datetime.now()}")

    # Get all articles
    all_articles = Article.objects.all()
    total_count = all_articles.count()
    print(f"📊 Total articles to process: {total_count}")

    # Counters for migration statistics
    stats = {"PENDING": 0, "APPROVED": 0, "DISCARDED": 0, "SENT": 0, "errors": 0}

    # Process articles in batches
    batch_size = 100
    processed = 0

    for article in all_articles:
        try:
            # Determine new status based on old fields
            old_validated = getattr(article, "validated", None)
            old_used = getattr(article, "used", None)

            if old_validated is True and old_used is True:
                new_status = Article.SENT
                stats["SENT"] += 1
            elif old_validated is True and old_used is False:
                new_status = Article.APPROVED
                stats["APPROVED"] += 1
            elif old_validated is False:
                new_status = Article.DISCARDED
                stats["DISCARDED"] += 1
            else:
                # validated is None or not set -> PENDING
                new_status = Article.PENDING
                stats["PENDING"] += 1

            # Update the article
            article.status = new_status
            article.save(update_fields=["status"])

            processed += 1

            # Progress indicator
            if processed % batch_size == 0:
                print(f"✅ Processed {processed}/{total_count} articles...")

        except Exception as e:
            print(f"❌ Error processing article {article.id}: {e}")
            stats["errors"] += 1
            continue

    print(f"\n🎉 Migration completed!")
    print(f"📊 Migration Statistics:")
    print(f"   - PENDING: {stats['PENDING']} articles")
    print(f"   - APPROVED: {stats['APPROVED']} articles")
    print(f"   - DISCARDED: {stats['DISCARDED']} articles")
    print(f"   - SENT: {stats['SENT']} articles")
    print(f"   - Errors: {stats['errors']} articles")
    print(f"   - Total processed: {processed}/{total_count}")

    return stats


def verify_migration():
    """
    Verify the migration was successful by checking status field distribution.
    """
    print("\n🔍 Verifying migration results...")

    # Count articles by status
    pending_count = Article.objects.filter(status=Article.PENDING).count()
    approved_count = Article.objects.filter(status=Article.APPROVED).count()
    discarded_count = Article.objects.filter(status=Article.DISCARDED).count()
    sent_count = Article.objects.filter(status=Article.SENT).count()

    total_with_status = pending_count + approved_count + discarded_count + sent_count
    total_articles = Article.objects.count()

    print(f"📈 Status Distribution:")
    print(f"   - PENDING: {pending_count}")
    print(f"   - APPROVED: {approved_count}")
    print(f"   - DISCARDED: {discarded_count}")
    print(f"   - SENT: {sent_count}")
    print(f"   - Total with status: {total_with_status}")
    print(f"   - Total articles: {total_articles}")

    if total_with_status == total_articles:
        print("✅ Migration verification successful - all articles have status field!")
    else:
        print(
            f"⚠️  Warning: {total_articles - total_with_status} articles missing status field"
        )

    # Show some example articles
    print(f"\n📝 Sample migrated articles:")
    sample_articles = Article.objects.all()[:5]
    for article in sample_articles:
        print(
            f"   - {article.id}: {article.status} | {article.title_it[:50] if article.title_it else 'No title'}..."
        )


def cleanup_old_fields():
    """
    Optional: Remove old validated and used fields from documents.
    WARNING: This is irreversible!
    """
    print("\n🧹 Cleanup old fields (validated, used)...")

    # Ask for confirmation
    response = input(
        "⚠️  This will permanently remove 'validated' and 'used' fields. Continue? (yes/no): "
    )
    if response.lower() != "yes":
        print("❌ Cleanup cancelled.")
        return

    # This would require direct MongoDB operations
    # For now, just print a warning
    print("⚠️  Manual cleanup required:")
    print("   Run this MongoDB command to remove old fields:")
    print("   db.articles.updateMany({}, {$unset: {validated: '', used: ''}})")


if __name__ == "__main__":
    print("🚀 Article Status Migration Script")
    print("=" * 50)

    try:
        # Run migration
        stats = migrate_article_status()

        # Verify results
        verify_migration()

        # Optional cleanup
        print("\n" + "=" * 50)
        cleanup_old_fields()

        print(f"\n✨ Migration script completed successfully!")
        print(f"⏰ Finished at: {datetime.now()}")

    except Exception as e:
        print(f"💥 Migration failed with error: {e}")
        sys.exit(1)
