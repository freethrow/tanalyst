import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from activities.models import Activity

User = get_user_model()


class Command(BaseCommand):
    help = 'Import activities from a CSV file'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to the CSV file containing activities data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing activities before importing'
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update existing activities if they match (by name, city, and dates)'
        )

    def parse_date(self, date_string):
        """Parse date string in various formats."""
        if not date_string or date_string.strip() == '':
            return None
        
        # Try different date formats
        formats = [
            '%d/%m/%Y',
            '%d/%m/%y',
            '%Y-%m-%d',
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

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        clear_existing = options['clear']
        update_existing = options['update']

        if clear_existing:
            count = Activity.objects.count()
            Activity.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {count} existing activities')
            )

        try:
            with open(csv_file, 'r', encoding='utf-8') as file:
                sample = file.read(1024)
                file.seek(0)
                
                if '\t' in sample:
                    delimiter = '\t'
                else:
                    delimiter = ','
                
                reader = csv.DictReader(file, delimiter=delimiter)
                
                required_fields = [
                    'tipo', 'mese', 'anno', 'nome_iniziativa', 'citta',
                    'data_inizio', 'data_fine', 'settore', 'descrizione',
                    'azione', 'ufficio'
                ]
                
                if reader.fieldnames is None:
                    raise CommandError('CSV file appears to be empty or invalid')
                
                missing_fields = set(required_fields) - set(reader.fieldnames)
                if missing_fields:
                    raise CommandError(
                        f'CSV is missing required columns: {", ".join(missing_fields)}'
                    )

                created_count = 0
                updated_count = 0
                skipped_count = 0

                for row_num, row in enumerate(reader, start=2):
                    try:
                        data_inizio = self.parse_date(row.get('data_inizio', ''))
                        data_fine = self.parse_date(row.get('data_fine', ''))

                        anno = None
                        if row.get('anno', '').strip():
                            try:
                                anno = int(row['anno'])
                            except ValueError:
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'Row {row_num}: Invalid year "{row["anno"]}"'
                                    )
                                )

                        mese = row.get('mese', '').strip()
                        if mese and len(mese) == 1:
                            mese = mese.zfill(2)

                        # Get admin user to add to responsabili
                        admin_user = User.objects.filter(is_superuser=True).first()
                        responsabili_list = [admin_user.username] if admin_user else []

                        activity_data = {
                            'tipo': row.get('tipo', '').strip(),
                            'mese': mese,
                            'anno': anno,
                            'nome_iniziativa': row.get('nome_iniziativa', '').strip(),
                            'citta': row.get('citta', '').strip(),
                            'data_inizio': data_inizio,
                            'data_fine': data_fine,
                            'settore': row.get('settore', '').strip(),
                            'descrizione': row.get('descrizione', '').strip(),
                            'azione': row.get('azione', '').strip(),
                            'ufficio': row.get('ufficio', '').strip(),
                            'responsabili': responsabili_list,
                        }

                        if update_existing:
                            existing = Activity.objects.filter(
                                nome_iniziativa=activity_data['nome_iniziativa'],
                                citta=activity_data['citta'],
                                data_inizio=data_inizio,
                            ).first()

                            if existing:
                                for key, value in activity_data.items():
                                    setattr(existing, key, value)
                                existing.save()
                                updated_count += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f'Row {row_num}: Updated "{activity_data["nome_iniziativa"]}"'
                                    )
                                )
                                continue

                        # Generate slug and check for duplicates
                        temp_activity = Activity(**activity_data)
                        generated_slug = temp_activity.generate_slug()

                        if Activity.objects.filter(slug=generated_slug).exists():
                            skipped_count += 1
                            self.stdout.write(
                                self.style.WARNING(
                                    f'Row {row_num}: Skipped "{activity_data["nome_iniziativa"]}" (slug already exists)'
                                )
                            )
                            continue

                        activity_data['slug'] = generated_slug
                        Activity.objects.create(**activity_data)
                        created_count += 1
                        
                        if created_count % 10 == 0:
                            self.stdout.write(f'Processed {created_count} activities...')

                    except Exception as e:
                        skipped_count += 1
                        self.stdout.write(
                            self.style.ERROR(
                                f'Row {row_num}: Error processing row - {str(e)}'
                            )
                        )
                        continue

                self.stdout.write(self.style.SUCCESS('\n' + '='*50))
                self.stdout.write(self.style.SUCCESS('Import Summary:'))
                self.stdout.write(self.style.SUCCESS(f'  Created: {created_count}'))
                if update_existing:
                    self.stdout.write(self.style.SUCCESS(f'  Updated: {updated_count}'))
                if skipped_count > 0:
                    self.stdout.write(self.style.WARNING(f'  Skipped: {skipped_count}'))
                self.stdout.write(self.style.SUCCESS('='*50))

        except FileNotFoundError:
            raise CommandError(f'File not found: {csv_file}')
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')
