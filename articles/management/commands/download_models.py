from django.core.management.base import BaseCommand
from sentence_transformers import SentenceTransformer


class Command(BaseCommand):
    help = 'Download and cache sentence transformer models'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            default='intfloat/multilingual-e5-base',
            help='Model name to download',
        )

    def handle(self, *args, **options):
        model_name = options['model']
        
        self.stdout.write(self.style.WARNING(f'🔄 Downloading model: {model_name}'))
        self.stdout.write(self.style.WARNING('This may take a few minutes on first run...'))
        
        try:
            model = SentenceTransformer(model_name)
            self.stdout.write(self.style.SUCCESS(f'✅ Model downloaded and cached successfully!'))
            self.stdout.write(self.style.SUCCESS(f'Model dimension: {model.get_sentence_embedding_dimension()}'))
            
            # Test encoding
            test_embedding = model.encode("test", show_progress_bar=False)
            self.stdout.write(self.style.SUCCESS(f'✅ Model tested successfully! Embedding shape: {test_embedding.shape}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Failed to download model: {str(e)}'))
            raise