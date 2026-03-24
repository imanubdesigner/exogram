# App: books

El núcleo de Exogram. Gestiona la biblioteca personal de cada usuario: libros, highlights,
notas, importación desde fuentes externas, búsqueda semántica y sincronización con Goodreads.

---

## Modelos

### `Author`

Autor de un libro.
- `name` (único efectivamente por normalización)
- `openlibrary_id` — ID en OpenLibrary, para enriquecimiento de metadatos.

### `Book`

Libro con metadatos.
- `title`, `isbn` (único, nullable)
- `authors` — ManyToMany con `Author`
- `cover_image` — portada subida o importada
- `openlibrary_id`, `average_rating`, `publish_year`, `genre`
- Los metadatos se enriquecen asíncronamente desde OpenLibrary vía tarea Celery.

### `Highlight`

El objeto central de la aplicación. Un subrayado o fragmento marcado de un libro.

- `user` → FK a `Profile`
- `book` → FK a `Book`
- `content` — texto del highlight
- `note` — nota personal del usuario sobre ese highlight (opcional)
- `location` — posición en el libro ("Loc 450-455", "Page 123")
- `visibility`: `private` | `unlisted` | `public`
- `embedding` — `VectorField(dimensions=384)`. Generado asíncronamente por Celery con el modelo ONNX. Nulo hasta que el worker lo procesa.
- `is_favorite`
- Índice HNSW en el campo `embedding` para búsqueda vectorial eficiente.

---

## Importación de highlights

### Kindle

Parser propio (`books/parsers/kindle_parser.py`) que procesa el archivo `My Clippings.txt`
que genera el Kindle. Extrae libros, autores, highlights y notas separando por el delimitador
`==========`. Tolerante a filas malformadas.

### Goodreads

Dos mecanismos:
1. **CSV de exportación de Goodreads:** importación manual del archivo que Goodreads genera en su panel de exportación.
2. **RSS feed de Goodreads:** sincronización periódica via Celery que consume el feed público de "currently reading" / "read" del usuario.

El scraper de Goodreads (`goodreads_reading_scraper.py`) parsea HTML externo, por lo que
es tolerante a cambios de estructura (errores en filas individuales no abortan la importación).

### Endpoint de importación

`POST /api/books/import/` — acepta archivos Kindle o Goodreads CSV.
Procesa de forma síncrona (parseo) y dispara las tareas de embedding de forma asíncrona.

---

## Embeddings y búsqueda semántica

### Generación de embeddings

Tras importar highlights, se disparan tareas Celery para generar los embeddings:

- **`generate_highlight_embedding(highlight_id)`**: genera el embedding de un highlight individual.
- **`batch_generate_embeddings(highlight_ids)`**: procesa múltiples highlights en sub-lotes de 16. Solo procesa highlights sin embedding (`embedding__isnull=True`), lo que la hace idempotente.
- Si el modelo ONNX no está disponible, la tarea devuelve un warning y no falla. Los highlights quedan sin embedding hasta que el modelo esté disponible.

### Búsqueda semántica

`POST /api/discovery/search/` con `{query: "texto de búsqueda", scope: "mine"|"network", limit: N}`

1. El texto de búsqueda se convierte a embedding con el mismo modelo ONNX.
2. Se ejecuta una búsqueda por similitud coseno en pgvector contra los highlights del scope elegido.
3. El índice HNSW en `Highlight.embedding` acelera la búsqueda.
4. Máximo configurable: 50 resultados (`max_value=50`).

---

## Tareas Celery

### `enrich_book_metadata(book_id)`

Consulta OpenLibrary API por ISBN. Si encuentra el libro, actualiza `publish_year` y `genre`.
Usa retry con exponential backoff ante errores de red (max 3 intentos).

### `generate_highlight_embedding(highlight_id)`

Ver sección de embeddings.

### `batch_generate_embeddings(highlight_ids)`

Ver sección de embeddings.

### `promote_trust_levels_task()`

Promueve en bulk a usuarios con ≥ 30 días de antigüedad de `depth=0` a `depth=1`.
Corre diariamente via Celery Beat.

### `beat_heartbeat()`

Escribe timestamp en Redis cada 60 segundos. El healthcheck del contenedor beat lo valida.

### Goodreads sync tasks

- `sync_goodreads_rss(profile_id)`: sincroniza el feed RSS de un usuario.
- `sync_goodreads_reading(profile_id)`: sincroniza el estado de "leyendo actualmente".
- `sync_all_goodreads_feeds()`: dispara sincronización para todos los usuarios con Goodreads habilitado.

---

## Visibilidad de highlights

| Valor | Comportamiento |
|---|---|
| `private` | Solo visible para el propio usuario |
| `unlisted` | No aparece en listados públicos pero accesible por URL directa |
| `public` | Visible en el perfil público y en el feed de la comunidad |

---

## Public notes

Los highlights con `visibility=public` y `note` no vacía son accesibles como "notas públicas".
`GET /api/books/public-notes/<nickname>/` devuelve las notas públicas de un usuario.

---

## Export

`GET /api/books/export/` — exporta todos los highlights del usuario autenticado en formato
CSV o JSON (según el header `Accept` o parámetro `format`).

---

## Endpoints principales

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/books/` | Listar libros del usuario |
| POST | `/api/books/import/` | Importar highlights (Kindle / Goodreads CSV) |
| GET/PATCH/DELETE | `/api/books/<id>/` | Detalle, edición y borrado de un libro |
| GET | `/api/books/<id>/highlights/` | Highlights de un libro |
| PATCH | `/api/highlights/<id>/` | Actualizar highlight (nota, visibilidad, favorito) |
| GET | `/api/books/export/` | Exportar highlights |
| GET | `/api/books/public-notes/<nickname>/` | Notas públicas de un usuario |
| POST | `/api/discovery/search/` | Búsqueda semántica por similitud |
