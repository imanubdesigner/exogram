# App: articles

Artículos editoriales del proyecto: filosofía, manifiesto, misión.

---

## Propósito

Contenido estático (pero gestionable desde el admin) que explica el proyecto a los lectores.
A diferencia del resto de las apps, el contenido no lo generan los usuarios: lo publica el equipo.

---

## Modelos

### `Article`

- `title`
- `slug` (único) — para URLs amigables
- `content` — texto del artículo (Markdown o HTML)
- `published_at`
- `is_published` — controla visibilidad pública

---

## Fixtures

La app incluye fixtures precargables con el contenido inicial del proyecto (filosofía, manifiesto).
Se cargan con:

```bash
python manage.py loaddata articles/fixtures/*.json
```

Se recomienda cargarlos en el primer deploy y en los entornos de desarrollo nuevos.

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/articles/` | Listar artículos publicados |
| GET | `/api/articles/<slug>/` | Detalle de un artículo |
