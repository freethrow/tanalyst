import json
from datetime import datetime, date
from django.core.management.base import BaseCommand
from activities.models import Activity


class Command(BaseCommand):
    help = 'Export activities from MongoDB to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Path to output JSON file. Default: activities_export_YYYYMMDD.json'
        )
        parser.add_argument(
            '--anno',
            type=int,
            default=None,
            help='Filter by year'
        )
        parser.add_argument(
            '--ufficio',
            type=str,
            default=None,
            help='Filter by office (Belgrado, Podgorica, Both)'
        )
        parser.add_argument(
            '--tipo',
            type=str,
            default=None,
            help='Filter by type'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit number of activities to export'
        )
        parser.add_argument(
            '--pretty',
            action='store_true',
            default=False,
            help='Output pretty-printed JSON'
        )

    def serialize_value(self, value):
        """Convert Python objects to JSON-serializable format."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, date):
            return value.isoformat()
        if hasattr(value, '__iter__') and not isinstance(value, (str, dict)):
            return [self.serialize_value(v) for v in value]
        return value

    def serialize_todo(self, todo):
        """Serialize a Todo embedded document."""
        return {
            'name': todo.name,
            'description': todo.description,
            'datetime': self.serialize_value(todo.datetime),
            'done': todo.done,
        }

    def handle(self, *args, **options):
        # Set up output file
        output_file = options['output']
        if not output_file:
            timestamp = datetime.now().strftime('%Y%m%d')
            output_file = f"activities_export_{timestamp}.json"

        # Build filter criteria
        filters = {}
        if options['anno']:
            filters['anno'] = options['anno']
        if options['ufficio']:
            filters['ufficio'] = options['ufficio']
        if options['tipo']:
            filters['tipo'] = options['tipo']

        # Query activities
        query = Activity.objects.filter(**filters)
        if options['limit']:
            query = query[:options['limit']]

        total_activities = query.count()
        self.stdout.write(f"Exporting {total_activities} activities to {output_file}")

        # Process and export activities
        activities_data = []

        for activity in query:
            activity_dict = {
                '_id': str(activity.id),
                'tipo': activity.tipo,
                'mese': activity.mese,
                'anno': activity.anno,
                'nome_iniziativa': activity.nome_iniziativa,
                'citta': activity.citta,
                'data_inizio': self.serialize_value(activity.data_inizio),
                'data_fine': self.serialize_value(activity.data_fine),
                'settore': activity.settore,
                'descrizione': activity.descrizione,
                'azione': activity.azione,
                'number_persons': activity.number_persons,
                'responsabile_iniziativa': activity.responsabile_iniziativa,
                'ufficio': activity.ufficio,
                'slug': activity.slug,
                'responsabili': activity.responsabili or [],
            }

            # Serialize todos if present
            if activity.todos:
                activity_dict['todos'] = [
                    self.serialize_todo(todo) for todo in activity.todos
                ]
            else:
                activity_dict['todos'] = []

            activities_data.append(activity_dict)

            # Progress reporting
            if len(activities_data) % 50 == 0:
                self.stdout.write(f"Processed {len(activities_data)} activities...")

        # Write JSON to file
        indent = 2 if options['pretty'] else None
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(activities_data, f, ensure_ascii=False, indent=indent)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully exported {len(activities_data)} activities to {output_file}"
        ))
