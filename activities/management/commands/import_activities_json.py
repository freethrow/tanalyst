import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from activities.models import Activity, Todo

User = get_user_model()


class Command(BaseCommand):
    help = 'Import activities from a JSON file into MongoDB'

    def add_arguments(self, parser):
        parser.add_argument(
            'input_file',
            type=str,
            help='Path to input JSON file with activities data'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=False,
            help='Perform a dry run without actually importing data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            default=False,
            help='Clear all existing activities before importing'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            default=False,
            help='Update existing activities if slug matches (default is to skip)'
        )
        parser.add_argument(
            '--regenerate-slugs',
            action='store_true',
            default=False,
            help='Regenerate slugs instead of using the ones from the import file'
        )

    def parse_date(self, date_string):
        """Parse date string in various formats."""
        if not date_string or date_string.strip() == '':
            return None

        # Try different date formats
        formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%d/%m/%y',
            '%d-%m-%Y',
        ]

        for fmt in formats:
            try:
                return datetime.strptime(date_string.strip(), fmt).date()
            except ValueError:
                continue

        self.stdout.write(
            self.style.WARNING(f'Could not parse date: {date_string}')
        )
        return None

    def parse_datetime(self, datetime_string):
        """Parse datetime string in ISO format."""
        if not datetime_string:
            return None

        try:
            return datetime.fromisoformat(datetime_string)
        except (ValueError, TypeError):
            return None

    def parse_todo(self, todo_data):
        """Parse a todo dictionary into a Todo embedded model instance."""
        return Todo(
            name=todo_data.get('name', ''),
            description=todo_data.get('description', ''),
            datetime=self.parse_datetime(todo_data.get('datetime')),
            done=todo_data.get('done', False),
        )

    def handle(self, *args, **options):
        input_file = options['input_file']
        dry_run = options['dry_run']
        clear_existing = options['clear']
        update_existing = options['update']
        regenerate_slugs = options['regenerate_slugs']

        if not os.path.exists(input_file):
            raise CommandError(f"File not found: {input_file}")

        # Read JSON file
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                activities_data = json.load(f)
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON file: {e}")
        except Exception as e:
            raise CommandError(f"Error reading file: {str(e)}")

        if not isinstance(activities_data, list):
            raise CommandError("JSON file must contain a list of activities")

        self.stdout.write(f"Found {len(activities_data)} activities in import file")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Clear existing if requested
        if clear_existing and not dry_run:
            count = Activity.objects.count()
            Activity.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing activities'))

        # Get existing slugs for duplicate checking
        existing_slugs = set(
            Activity.objects.values_list('slug', flat=True).exclude(slug__isnull=True)
        )

        # Initialize counters
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0

        for idx, activity_data in enumerate(activities_data, start=1):
            try:
                # Remove _id field to avoid conflicts
                activity_data.pop('_id', None)

                # Parse dates
                data_inizio = None
                data_fine = None
                if activity_data.get('data_inizio'):
                    data_inizio = self.parse_date(activity_data['data_inizio'])
                if activity_data.get('data_fine'):
                    data_fine = self.parse_date(activity_data['data_fine'])

                # Parse todos
                todos = []
                if activity_data.get('todos'):
                    for todo_data in activity_data['todos']:
                        todos.append(self.parse_todo(todo_data))

                # Get admin user to add to responsabili
                admin_user = User.objects.filter(is_superuser=True).first()
                responsabili_list = activity_data.get('responsabili', [])
                if admin_user and admin_user.username not in responsabili_list:
                    responsabili_list.append(admin_user.username)

                # Build activity fields
                activity_fields = {
                    'tipo': activity_data.get('tipo'),
                    'mese': activity_data.get('mese'),
                    'anno': activity_data.get('anno'),
                    'nome_iniziativa': activity_data.get('nome_iniziativa'),
                    'citta': activity_data.get('citta'),
                    'data_inizio': data_inizio,
                    'data_fine': data_fine,
                    'settore': activity_data.get('settore'),
                    'descrizione': activity_data.get('descrizione'),
                    'azione': activity_data.get('azione'),
                    'number_persons': activity_data.get('number_persons'),
                    'ufficio': activity_data.get('ufficio'),
                    'responsabili': responsabili_list,
                    'todos': todos if todos else None,
                }

                # Handle slug
                imported_slug = activity_data.get('slug')

                # Check if this is an update scenario
                if imported_slug and imported_slug in existing_slugs and not regenerate_slugs:
                    if update_existing:
                        # Update existing activity
                        if not dry_run:
                            activity = Activity.objects.get(slug=imported_slug)
                            for key, value in activity_fields.items():
                                setattr(activity, key, value)
                            activity.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'[{idx}] Updated: {activity_fields.get("nome_iniziativa")}')
                        )
                    else:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.WARNING(f'[{idx}] Skipped (exists): {activity_fields.get("nome_iniziativa")}')
                        )
                    continue

                # Create new activity
                if not regenerate_slugs and imported_slug:
                    activity_fields['slug'] = imported_slug

                if not dry_run:
                    activity = Activity(**activity_fields)
                    if regenerate_slugs or not activity_fields.get('slug'):
                        activity.slug = activity.generate_slug()
                    activity.save()
                    existing_slugs.add(activity.slug)

                created_count += 1

                if created_count % 20 == 0:
                    self.stdout.write(f'Created {created_count} activities...')

            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'[{idx}] Error: {str(e)}')
                )

        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Import Summary:'))
        self.stdout.write(f'  Total in file: {len(activities_data)}')
        self.stdout.write(self.style.SUCCESS(f'  Created: {created_count}'))
        if update_existing:
            self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'  Skipped: {skipped_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'  Errors: {error_count}'))
        self.stdout.write('=' * 50)

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No actual changes were made"))
        else:
            self.stdout.write(self.style.SUCCESS("\nImport completed"))
