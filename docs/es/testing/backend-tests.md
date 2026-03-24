# Tests del backend

Cobertura por app y cómo ejecutarlos.

---

## Ejecutar los tests

```bash
# Todos los tests con cobertura
docker compose exec backend coverage run --source='.' manage.py test --verbosity=2

# Solo una app
docker compose exec backend python manage.py test accounts --verbosity=2

# Solo un módulo o test case
docker compose exec backend python manage.py test books.tests.test_parsers --verbosity=2
docker compose exec backend python manage.py test accounts.tests.ProfileUpdateTest --verbosity=2

# Reporte de cobertura
docker compose exec backend coverage report
docker compose exec backend coverage html   # genera htmlcov/
```

---

## Cobertura por app

### `accounts/tests.py`

| Test case | Qué cubre |
|---|---|
| `ProfileUpdateTest` | PATCH bio, PATCH nickname (incluyendo sincronización con User.username), nickname duplicado rechazado, acceso sin auth rechazado, upload JPEG/PNG válido, archivo no-imagen rechazado, avatar > 2 MB rechazado. |
| `PublicProfileTest` | Perfil público visible sin auth, perfil con hermit mode devuelve 404, hermit profile visible para el propietario, perfil inexistente devuelve 404. |
| `TokenRefreshTest` | Refresh con cookie válida devuelve nuevo access token, refresh sin cookie rechazado. |
| `WaitlistTest` | Unirse a la waitlist crea el entry, idempotencia (doble POST con mismo email → 200 y un solo entry), falta de email → 400, listado por usuario no-staff → 403, listado por staff → 200. |
| `ValidateInvitationTest` | Token válido → 200 con `valid: true`, token expirado (>72h) → 400 con `valid: false`, token inexistente → 404. |
| `AvatarSanitizationTest` | Re-codificación al subir (verifica que Pillow.open fue llamado), PNG RGBA aceptado. |
| `CurrentUserViewTest` | GET /me/ sin auth → 401, con auth → 200 con nickname, password no expuesto en respuesta. |

### `books/tests/`

| Archivo | Qué cubre |
|---|---|
| `test_auth_views.py` | Endpoints de autenticación específicos de la app books (login requerido para acciones de biblioteca). |
| `test_export_views.py` | Export de highlights: formato correcto, solo los highlights del usuario autenticado. |
| `test_goodreads_activation.py` | Activación de la integración con Goodreads. |
| `test_goodreads_scraper.py` | Parser del HTML de Goodreads: libros leídos, estado de lectura, manejo de filas malformadas. |
| `test_highlight_import.py` | Importación de archivos Kindle y Goodreads CSV: highlights detectados, libros creados, duplicados manejados. |
| `test_highlight_update.py` | PATCH de highlight: nota, visibilidad, favorito. Propietario puede editar, otro usuario no. |
| `test_models.py` | Modelos Book, Highlight, Author: creación, relaciones, defaults. |
| `test_parsers.py` | KindleParser: parsing de clippings.txt, extracción de libros y autores, manejo de formatos de fecha. |
| `test_public_notes.py` | Notas públicas: solo highlights con `visibility=public` y nota no vacía, de usuarios sin hermit mode. |
| `test_user_models_abc.py` | Modelos relacionados con el usuario en la app books. |

### `social/tests.py`

| Test case | Qué cubre |
|---|---|
| `ModerationTest` | `analyze_toxicity`: texto limpio → score bajo, texto tóxico → score alto, múltiples URLs → score elevado, CAPS abuse → score elevado. |

### `threads/tests.py`

Cubre creación de hilos, restricción de red (solo usuarios en la misma red pueden crear hilos),
idempotencia (segundo intento entre los mismos usuarios devuelve el hilo existente),
envío de mensajes, listado de mensajes con paginación.

### `affinity/tests.py`

| Test case | Qué cubre |
|---|---|
| `UserClusterModelTest` | Creación de UserCluster, compute_user_centroid con highlights, update_user_cluster. |

---

## Tests de frontend

Ver [frontend-tests.md](./frontend-tests.md).

---

## Agregar tests nuevos

1. Crear el test en el archivo correspondiente a la app (`accounts/tests.py`, etc.)
   o en `books/tests/test_<feature>.py` si la app ya tiene múltiples archivos.
2. Heredar de `django.test.TestCase` para tests con DB.
3. Usar `rest_framework.test.APIClient` para tests de endpoints.
4. Los helpers `_make_user` y `_login` de `accounts/tests.py` son un buen patrón a seguir.

```python
from django.test import TestCase
from rest_framework.test import APIClient

class MiFeatureTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        # setup...

    def test_algo(self):
        response = self.client.get('/api/mi-endpoint/')
        self.assertEqual(response.status_code, 200)
```

5. Si el test necesita que el throttling esté desactivado, `settings_ci.py` ya lo desactiva para toda la suite. Si el test necesita verificar throttling específicamente, usar `@override_settings`.
