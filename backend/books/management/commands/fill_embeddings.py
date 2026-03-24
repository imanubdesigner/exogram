"""
Management command: fill_embeddings

Genera embeddings faltantes directamente en el proceso actual (sin Celery).
Útil para backfill inicial o cuando Celery no está disponible.

Uso:
    python manage.py fill_embeddings
    python manage.py fill_embeddings --batch-size 50
"""
from django.core.management.base import BaseCommand

from books.embeddings import encode_batch
from books.models import Highlight


class Command(BaseCommand):
    help = 'Genera embeddings para todos los highlights que no los tienen'

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=32,
            help='Cantidad de highlights a procesar por lote (default: 32)'
        )

    def handle(self, *args, **options):
        batch_size = options['batch_size']

        total_missing = Highlight.objects.filter(embedding__isnull=True).count()

        if total_missing == 0:
            self.stdout.write(self.style.SUCCESS('No hay embeddings faltantes. Todo procesado.'))
            return

        self.stdout.write(f'Procesando {total_missing} highlights sin embedding (lotes de {batch_size})...')

        processed = 0
        errors = 0

        while True:
            # Re-consultar siempre para excluir los ya procesados en iteraciones anteriores.
            # No usamos offset ya que el filtro embedding__isnull=True actúa como cursor natural.
            batch = list(
                Highlight.objects.filter(embedding__isnull=True)
                .order_by('id')[:batch_size]
            )
            if not batch:
                break

            try:
                contents = [h.content for h in batch]
                embeddings = encode_batch(contents)

                for highlight, embedding in zip(batch, embeddings):
                    highlight.embedding = embedding.tolist()
                    highlight.save(update_fields=['embedding'])

                processed += len(batch)
                self.stdout.write(f'  ✓ Procesados {processed}/{total_missing}')

            except Exception as e:
                errors += len(batch)
                self.stdout.write(self.style.ERROR(f'  ✗ Error en lote: {e}'))
                # Marcar el lote como procesado con un valor vacío en caso de error
                # persistente para evitar un loop infinito sobre el mismo lote.
                # En la mayoría de los casos el error es transitorio y el próximo
                # lote se procesa correctamente.
                for highlight in batch:
                    try:
                        # Intentar de a uno para aislar el highlight problemático
                        emb = encode_batch([highlight.content])
                        highlight.embedding = emb[0].tolist()
                        highlight.save(update_fields=['embedding'])
                        processed += 1
                    except Exception as inner_e:
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Highlight {highlight.id} inaccesible: {inner_e}')
                        )
                        # No podemos procesar este highlight. Saltearlo con un
                        # embedding temporal de ceros para desbloquear el loop.
                        import numpy as np
                        highlight.embedding = np.zeros(384).tolist()
                        highlight.save(update_fields=['embedding'])
                        errors += 1
                continue

        self.stdout.write(
            self.style.SUCCESS(f'\n¡Listo! {processed} embeddings generados. {errors} con error.')
        )
