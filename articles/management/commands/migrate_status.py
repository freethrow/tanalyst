from django.core.management.base import BaseCommand
from articles.models import Article
from datetime import datetime


class Command(BaseCommand):
    help = "Migrate articles from validated/used fields to status field"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of articles to process in each batch (default: 100)",
        )
        parser.add_argument(
            "--cleanup-old-fields",
            action="store_true",
            help="Remove old validated and used fields from MongoDB documents",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        cleanup_old_fields = options["cleanup_old_fields"]

        if cleanup_old_fields:
            self._cleanup_old_fields(dry_run)
            return

        self.stdout.write(self.style.SUCCESS("🔄 Starting status field migration..."))

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN MODE - No changes will be made")
            )

        # Get all articles
        all_articles = Article.objects.all()
        total_count = all_articles.count()

        self.stdout.write(f"📊 Total articles to process: {total_count}")

        # Counters
        stats = {"PENDING": 0, "APPROVED": 0, "DISCARDED": 0, "SENT": 0, "errors": 0}

        processed = 0

        for article in all_articles:
            try:
                # Get old field values
                old_validated = getattr(article, "validated", None)
                old_used = getattr(article, "used", None)

                # Determine new status
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
                    new_status = Article.PENDING
                    stats["PENDING"] += 1

                # Show what would change in dry run
                if dry_run:
                    current_status = getattr(article, "status", "None")
                    if processed < 5:  # Show first 5 examples
                        self.stdout.write(
                            f"   Article {article.id}: validated={old_validated}, used={old_used} -> status={new_status} (currently: {current_status})"
                        )
                else:
                    # Actually update the article
                    article.status = new_status
                    article.save(update_fields=["status"])

                processed += 1

                # Progress indicator
                if processed % batch_size == 0:
                    self.stdout.write(
                        f"✅ Processed {processed}/{total_count} articles..."
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error processing article {article.id}: {e}")
                )
                stats["errors"] += 1
                continue

        # Show results
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Migration {'simulation' if dry_run else 'completed'}!"
            )
        )
        self.stdout.write("📊 Statistics:")
        self.stdout.write(f"   - PENDING: {stats['PENDING']} articles")
        self.stdout.write(f"   - APPROVED: {stats['APPROVED']} articles")
        self.stdout.write(f"   - DISCARDED: {stats['DISCARDED']} articles")
        self.stdout.write(f"   - SENT: {stats['SENT']} articles")
        self.stdout.write(f"   - Errors: {stats['errors']} articles")
        self.stdout.write(f"   - Total processed: {processed}/{total_count}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING("\n💡 Run without --dry-run to apply changes")
            )
        else:
            # Verify migration
            self._verify_migration()

    def _verify_migration(self):
        """Verify the migration results"""
        self.stdout.write("\n🔍 Verifying migration...")

        pending_count = Article.objects.filter(status=Article.PENDING).count()
        approved_count = Article.objects.filter(status=Article.APPROVED).count()
        discarded_count = Article.objects.filter(status=Article.DISCARDED).count()
        sent_count = Article.objects.filter(status=Article.SENT).count()

        total_with_status = (
            pending_count + approved_count + discarded_count + sent_count
        )
        total_articles = Article.objects.count()

        self.stdout.write("📈 Current Status Distribution:")
        self.stdout.write(f"   - PENDING: {pending_count}")
        self.stdout.write(f"   - APPROVED: {approved_count}")
        self.stdout.write(f"   - DISCARDED: {discarded_count}")
        self.stdout.write(f"   - SENT: {sent_count}")

        if total_with_status == total_articles:
            self.stdout.write(self.style.SUCCESS("✅ All articles have status field!"))
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"⚠️  {total_articles - total_with_status} articles missing status"
                )
            )

    def _cleanup_old_fields(self, dry_run=False):
        """Remove old validated and used fields from MongoDB documents"""
        from pymongo import MongoClient
        from django.conf import settings
        import os

        self.stdout.write(
            self.style.SUCCESS("🧹 Cleaning up old fields (validated, used)...")
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN MODE - No changes will be made")
            )

        try:
            # Connect to MongoDB directly
            # Get MongoDB connection details from Django settings
            db_config = settings.DATABASES["default"]

            # Parse MongoDB URI or construct connection
            if "HOST" in db_config:
                mongo_uri = db_config["HOST"]
            else:
                mongo_uri = os.getenv("MONGODB_URI", "mongodb://localhost:7587/?directConnection=true")

            client = MongoClient(mongo_uri)
            db = client[db_config["NAME"]]
            collection = db["articles"]

            # Check how many documents have the old fields
            docs_with_validated = collection.count_documents(
                {"validated": {"$exists": True}}
            )
            docs_with_used = collection.count_documents({"used": {"$exists": True}})

            self.stdout.write(f"📊 Documents with old fields:")
            self.stdout.write(f"   - 'validated' field: {docs_with_validated}")
            self.stdout.write(f"   - 'used' field: {docs_with_used}")

            if docs_with_validated == 0 and docs_with_used == 0:
                self.stdout.write(
                    self.style.SUCCESS("✅ No old fields found - cleanup not needed!")
                )
                return

            if not dry_run:
                # Remove the old fields
                result = collection.update_many(
                    {},  # Match all documents
                    {"$unset": {"validated": "", "used": ""}},  # Remove these fields
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"✅ Cleaned up {result.modified_count} documents"
                    )
                )

                # Verify cleanup
                remaining_validated = collection.count_documents(
                    {"validated": {"$exists": True}}
                )
                remaining_used = collection.count_documents({"used": {"$exists": True}})

                if remaining_validated == 0 and remaining_used == 0:
                    self.stdout.write(
                        self.style.SUCCESS("🎉 All old fields successfully removed!")
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️  Some fields remain: validated={remaining_validated}, used={remaining_used}"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.WARNING("💡 Run without --dry-run to remove old fields")
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error during cleanup: {e}"))
        finally:
            if "client" in locals():
                client.close()
