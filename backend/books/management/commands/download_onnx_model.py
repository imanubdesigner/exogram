"""
Django management command para descargar el modelo ONNX.

Modelo: paraphrase-multilingual-MiniLM-L12-v2 (Xenova/HuggingFace)
Tamaño: ~470MB en disco, ~1GB en RAM en runtime

Uso:
    python manage.py download_onnx_model
    python manage.py download_onnx_model --cache-dir /ruta/personalizada
"""
from django.core.management.base import BaseCommand

from books.embeddings import PureONNXEmbeddingModel


class Command(BaseCommand):
    help = 'Descarga y cachea el modelo paraphrase-multilingual-MiniLM-L12-v2 en formato ONNX'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cache-dir',
            type=str,
            default='./models_cache',
            help='Directorio donde cachear el modelo (default: ./models_cache)'
        )

    def handle(self, *args, **options):
        cache_dir = options['cache_dir']

        self.stdout.write(
            f"Descargando modelo ONNX a {cache_dir}...\n"
            f"⚠️  El modelo pesa ~470MB. La descarga puede tardar varios minutos."
        )

        try:
            # Instanciar el modelo lo descarga automáticamente si no está en cache
            model = PureONNXEmbeddingModel(cache_dir=cache_dir)

            # Smoke test con un texto de ejemplo
            self.stdout.write("Verificando modelo con texto de prueba...")
            test_embedding = model.encode("El cosmos es todo lo que existe, existió o existirá.")

            self.stdout.write(self.style.SUCCESS(
                f'✓ Modelo descargado y verificado exitosamente\n'
                f'  Nombre: paraphrase-multilingual-MiniLM-L12-v2\n'
                f'  Dimensiones: {test_embedding.shape[1]} (esperado: 384)\n'
                f'  Ubicación: {cache_dir}'
            ))

        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f'✗ Error: {e}\n'
                f'  Verificá tu conexión a internet e intentá de nuevo.\n'
                f'  El modelo se descargará automáticamente en el primer uso si no está disponible.'
            ))
