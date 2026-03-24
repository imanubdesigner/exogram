"""
Exportación de highlights a formato Obsidian.

Genera un archivo ZIP con un .md por libro, con YAML frontmatter
y WikiLinks entre libros del mismo autor y libros semánticamente relacionados.
"""
import io
import zipfile
from datetime import datetime

import numpy as np
from django.http import HttpResponse
from rest_framework import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Highlight


class ObsidianExportView(views.APIView):
    """
    Exporta todos los highlights del usuario en formato Obsidian.

    GET /api/me/export/obsidian/

    Retorna un ZIP con:
    - Un archivo .md por libro
    - YAML frontmatter con metadata
    - WikiLinks entre libros del mismo autor
    - Highlights formateados como blockquotes
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile = request.user.profile
        highlights = Highlight.objects.filter(
            user=profile
        ).select_related('book').prefetch_related('book__authors').order_by(
            'book__title', 'created_at'
        )

        if not highlights.exists():
            return Response(
                {'error': 'No tienes highlights para exportar'},
                status=400
            )

        # Agrupar por libro
        books_data = {}
        for h in highlights:
            book_id = h.book_id
            if book_id not in books_data:
                books_data[book_id] = {
                    'book': h.book,
                    'highlights': []
                }
            books_data[book_id]['highlights'].append(h)

        # Calcular centroides por libro (promedio de embeddings de highlights)
        book_centroids = self._compute_book_centroids(books_data)

        # Generar mapa de libros relacionados (semánticos + mismo autor)
        author_books = {}
        for data in books_data.values():
            book = data['book']
            for author in book.authors.all():
                if author.name not in author_books:
                    author_books[author.name] = []
                author_books[author.name].append(book.title)

        related_books = self._compute_related_books(books_data, book_centroids, top_n=5)

        # Generar ZIP
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for data in books_data.values():
                book = data['book']
                book_highlights = data['highlights']
                authors = [a.name for a in book.authors.all()]

                md_content = self._generate_markdown(
                    book, book_highlights, authors, author_books,
                    related_books.get(book.id, [])
                )

                # Sanitizar nombre de archivo
                safe_title = self._sanitize_filename(book.title)
                zf.writestr(f"Exogram/Libros/{safe_title}.md", md_content)

            # Generar notas de autores (backlink nodes)
            for author_name, book_titles in author_books.items():
                author_md = self._generate_author_note(
                    author_name, book_titles, books_data
                )
                safe_author = self._sanitize_filename(author_name)
                zf.writestr(f"Exogram/Autores/{safe_author}.md", author_md)

            # Agregar archivo índice
            index_md = self._generate_index(books_data, author_books, profile)
            zf.writestr("Exogram/índice.md", index_md)

        buffer.seek(0)

        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/zip'
        )
        response['Content-Disposition'] = (
            f'attachment; filename="exogram-export-'
            f'{datetime.now().strftime("%Y%m%d")}.zip"'
        )
        return response

    def _generate_markdown(self, book, highlights, authors, author_books, related_titles):
        """Genera el contenido .md de un libro."""
        authors_str = ', '.join(authors)

        # YAML Frontmatter
        lines = [
            '---',
            f'title: "{book.title}"',
            f'author: "{authors_str}"',
        ]
        if book.isbn:
            lines.append(f'isbn: "{book.isbn}"')
        if book.publish_year:
            lines.append(f'year: {book.publish_year}')
        if book.genre:
            lines.append(f'genre: "{book.genre}"')
            # Tags para navegación en Obsidian
            lines.append(f'tags: ["{book.genre}"]')

        lines.extend([
            f'highlights: {len(highlights)}',
            f'exported: "{datetime.now().strftime("%Y-%m-%d")}"',
            'source: Exogram',
        ])

        # Libros semánticamente relacionados en frontmatter
        if related_titles:
            lines.append('related_books:')
            for title in related_titles:
                lines.append(f'  - "{title}"')

        lines.extend([
            '---',
            '',
            f'# {book.title}',
        ])

        # Autores como WikiLinks (backlinks hacia notas de autor)
        author_links = [f'[[Autores/{self._sanitize_filename(a)}|{a}]]' for a in authors]
        lines.append(f'*{" · ".join(author_links)}*')
        lines.append('')

        # WikiLinks a otros libros del mismo autor
        related = set()
        for author in authors:
            for title in author_books.get(author, []):
                if title != book.title:
                    related.add(title)

        if related:
            lines.append('## Otros libros del autor')
            for title in sorted(related):
                safe = self._sanitize_filename(title)
                lines.append(f'- [[Libros/{safe}|{title}]]')
            lines.append('')

        # Libros semánticamente relacionados (por embeddings)
        if related_titles:
            lines.append('## Libros relacionados')
            for title in related_titles:
                safe = self._sanitize_filename(title)
                lines.append(f'- [[Libros/{safe}|{title}]]')
            lines.append('')

        # Highlights
        lines.append('## Highlights')
        lines.append('')

        for h in highlights:
            lines.append(f'> {h.content}')
            lines.append(f'> — *{h.location}*')
            if h.note:
                lines.append('')
                lines.append(f'📝 {h.note}')
            lines.append('')

        return '\n'.join(lines)

    def _compute_book_centroids(self, books_data):
        """
        Calcula el centroide semántico de cada libro como el promedio de
        los embeddings de sus highlights.

        Returns:
            dict[int, np.ndarray]: book_id → centroid vector (384-dim)
        """
        centroids = {}
        for book_id, data in books_data.items():
            embeddings = [
                h.embedding for h in data['highlights']
                if h.embedding is not None
            ]
            if embeddings:
                centroids[book_id] = np.mean(embeddings, axis=0)
        return centroids

    def _compute_related_books(self, books_data, book_centroids, top_n=5):
        """
        Para cada libro con centroide, encuentra los top_n libros más
        similares usando similitud coseno en memoria.

        Returns:
            dict[int, list[str]]: book_id → [títulos de libros relacionados]
        """
        if len(book_centroids) < 2:
            return {}

        book_ids = list(book_centroids.keys())
        # Armar matriz de centroides normalizados
        matrix = np.array([book_centroids[bid] for bid in book_ids], dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)  # Evitar división por cero
        matrix_normalized = matrix / norms

        # Cosine similarity: producto punto de vectores normalizados
        similarity_matrix = matrix_normalized @ matrix_normalized.T

        related = {}
        for i, bid in enumerate(book_ids):
            # Excluir a sí mismo (diagonal) y ordenar por similitud descendente
            scores = similarity_matrix[i]
            ranked_indices = np.argsort(-scores)
            titles = []
            for j in ranked_indices:
                if j == i:
                    continue
                other_id = book_ids[j]
                titles.append(books_data[other_id]['book'].title)
                if len(titles) >= top_n:
                    break
            related[bid] = titles

        return related

    def _generate_author_note(self, author_name, book_titles, books_data):
        """
        Genera una nota de autor para Obsidian.

        Crea un nodo en el grafo que recibe backlinks de cada libro del
        autor, completando la estructura bidireccional.
        """
        total_highlights = 0
        for data in books_data.values():
            book = data['book']
            if any(a.name == author_name for a in book.authors.all()):
                total_highlights += len(data['highlights'])

        lines = [
            '---',
            f'title: "{author_name}"',
            'type: autor',
            f'libros: {len(book_titles)}',
            f'highlights_totales: {total_highlights}',
            f'exported: "{datetime.now().strftime("%Y-%m-%d")}"',
            'source: Exogram',
            '---',
            '',
            f'# {author_name}',
            '',
            '## Libros',
            '',
        ]

        for title in sorted(book_titles):
            safe = self._sanitize_filename(title)
            # Buscar cantidad de highlights para este libro
            count = 0
            for data in books_data.values():
                if data['book'].title == title:
                    count = len(data['highlights'])
                    break
            lines.append(f'- [[Libros/{safe}|{title}]] ({count} highlights)')

        lines.extend([
            '',
            '---',
            f'*{total_highlights} highlights en {len(book_titles)} libro{"s" if len(book_titles) != 1 else ""}*',
        ])

        return '\n'.join(lines)

    def _generate_index(self, books_data, author_books, profile):
        """Genera el archivo índice."""
        lines = [
            '---',
            'title: "Exogram — Índice de Exportación"',
            f'exported: "{datetime.now().strftime("%Y-%m-%d")}"',
            f'user: "{profile.nickname}"',
            '---',
            '',
            '# Exogram — Mis Highlights',
            '',
            f'Exportado el {datetime.now().strftime("%d/%m/%Y")}',
            '',
            '## Libros',
            '',
        ]

        total_highlights = 0
        for data in sorted(books_data.values(), key=lambda d: d['book'].title):
            book = data['book']
            count = len(data['highlights'])
            total_highlights += count
            safe = self._sanitize_filename(book.title)
            authors = ', '.join(a.name for a in book.authors.all())
            lines.append(f'- [[Libros/{safe}|{book.title}]] — *{authors}* ({count} highlights)')

        # Sección de autores
        if author_books:
            lines.extend([
                '',
                '## Autores',
                '',
            ])
            for author_name in sorted(author_books.keys()):
                safe_author = self._sanitize_filename(author_name)
                book_count = len(author_books[author_name])
                suffix = "s" if book_count != 1 else ""
                lines.append(f'- [[Autores/{safe_author}|{author_name}]] ({book_count} libro{suffix})')

        lines.extend([
            '',
            '## Estadísticas',
            '',
            f'- **Libros**: {len(books_data)}',
            f'- **Autores**: {len(author_books)}',
            f'- **Highlights**: {total_highlights}',
        ])

        return '\n'.join(lines)

    def _sanitize_filename(self, name):
        """Sanitiza un string para usar como nombre de archivo."""
        # Caracteres no válidos en filenames
        invalid = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        result = name
        for char in invalid:
            result = result.replace(char, '-')
        return result.strip()[:100]


class BookMarkdownExportView(views.APIView):
    """
    Exporta los highlights de un único libro en formato Markdown con frontmatter.

    GET /api/me/export/books/<book_id>/markdown/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, book_id):
        profile = request.user.profile
        highlights_qs = Highlight.objects.filter(
            user=profile,
            book_id=book_id
        ).select_related('book').prefetch_related('book__authors').order_by('created_at')

        if not highlights_qs.exists():
            return Response(
                {'error': 'No se encontraron highlights para ese libro'},
                status=404
            )

        highlights = list(highlights_qs)
        book = highlights[0].book
        authors = [a.name for a in book.authors.all()]
        markdown = self._generate_markdown(book, highlights, authors, profile.nickname)

        safe_title = self._sanitize_filename(book.title)
        response = HttpResponse(markdown, content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{safe_title}.md"'
        return response

    def _generate_markdown(self, book, highlights, authors, nickname):
        authors_str = ', '.join(authors) if authors else 'Autor desconocido'
        today = datetime.now().strftime("%Y-%m-%d")

        lines = [
            '---',
            f'title: "{self._escape_yaml(book.title)}"',
            f'author: "{self._escape_yaml(authors_str)}"',
            f'book_id: {book.id}',
            f'user: "{self._escape_yaml(nickname)}"',
            f'highlights: {len(highlights)}',
            f'exported: "{today}"',
            'source: "Exogram"',
        ]

        if book.isbn:
            lines.append(f'isbn: "{self._escape_yaml(book.isbn)}"')
        if book.publish_year:
            lines.append(f'year: {book.publish_year}')
        if book.genre:
            lines.append(f'genre: "{self._escape_yaml(book.genre)}"')

        lines.extend([
            '---',
            '',
            f'# {book.title}',
            f'*{authors_str}*',
            '',
            '## Highlights',
            '',
        ])

        for idx, highlight in enumerate(highlights, start=1):
            created_label = highlight.created_at.strftime('%Y-%m-%d')
            lines.append(f'### {idx}. {created_label}')
            lines.append(f'> {highlight.content}')
            if highlight.location:
                lines.append(f'> — *{highlight.location}*')
            if highlight.note:
                lines.extend([
                    '',
                    f'Nota: {highlight.note}',
                ])
            lines.append('')

        return '\n'.join(lines)

    def _escape_yaml(self, value):
        return str(value).replace('\\', '\\\\').replace('"', '\\"')

    def _sanitize_filename(self, name):
        invalid = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        result = name
        for char in invalid:
            result = result.replace(char, '-')
        return result.strip()[:100]
