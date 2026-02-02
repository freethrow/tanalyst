from django.core.management.base import BaseCommand
from activities.models import Activity


class Command(BaseCommand):
    help = 'Generate and save slugs for activities that do not have one'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            default=False,
            help='Regenerate slugs for ALL activities, not just those missing slugs'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Show what would be done without making changes'
        )

    def handle(self, *args, **options):
        regenerate_all = options['all']
        dry_run = options['dry_run']

        if regenerate_all:
            activities = Activity.objects.all()
            self.stdout.write(f"Regenerating slugs for ALL {activities.count()} activities")
        else:
            activities = Activity.objects.filter(slug__isnull=True) | Activity.objects.filter(slug='')
            self.stdout.write(f"Found {activities.count()} activities without slugs")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))

        updated_count = 0
        error_count = 0

        for activity in activities:
            try:
                old_slug = activity.slug
                new_slug = activity.generate_slug()

                if dry_run:
                    self.stdout.write(
                        f"  {activity.nome_iniziativa} -> {new_slug}"
                    )
                else:
                    activity.slug = new_slug
                    activity.save(update_fields=['slug'])

                updated_count += 1

                if updated_count % 20 == 0:
                    self.stdout.write(f"Processed {updated_count} activities...")

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"Error processing {activity.nome_iniziativa}: {e}")
                )

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f"Updated: {updated_count}"))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f"Errors: {error_count}"))
        self.stdout.write('=' * 50)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No actual changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS("\nSlug generation completed"))
