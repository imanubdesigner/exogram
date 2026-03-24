# Dependencias del backend

Referencia de todos los paquetes en `backend/requirements.txt`.

---

| Paquete | Versión | Propósito | Por qué este y no otro |
|---|---|---|---|
| `Django` | 5.2.12 | Framework web principal | LTS hasta 2028. Ver [ADR 0008](../adr/0008-django-5-lts.md). |
| `djangorestframework` | 3.15.2 | API REST sobre Django | Estándar de facto para APIs Django. Integración nativa con autenticación, permisos, throttling y paginación. |
| `djangorestframework-simplejwt` | 5.5.1 | JWT: generación, validación, blacklist | Corrige CVE-2024-22513. Token blacklist incluida como app instalable. |
| `django-cors-headers` | 4.6.0 | Headers CORS | Única dependencia para CORS en Django, bien mantenida. |
| `django-celery-beat` | 2.9.0 | Schedule de tareas en PostgreSQL | Persiste schedule entre reinicios. Ver [ADR 0005](../adr/0005-celery-beat-postgresql.md). |
| `celery` | 5.4.0 | Cola de tareas asíncronas | Estándar para tareas en background en Django. Retry, backoff, beat incluidos. |
| `redis` | 5.2.1 | Cliente Python de Redis | Usado como broker de Celery y para el heartbeat del beat. |
| `psycopg2` | 2.9.10 | Driver PostgreSQL compilado | La versión compilada (no `psycopg2-binary`) es la recomendada para producción por estabilidad. Requiere `libpq-dev` en el sistema. |
| `pgvector` | 0.3.6 | Integración Django para pgvector | Provee `VectorField`, `HnswIndex` y operadores de distancia para Django ORM. |
| `python-decouple` | 3.8 | Lectura de variables de entorno | Lee desde `.env` y variables de entorno del sistema. Más explícito que `os.environ.get` en toda la codebase. |
| `Pillow` | 12.1.1 | Procesamiento de imágenes | Usado para validación y re-codificación de avatares. Versión 12.x corrige vulnerabilidades de parsing de imágenes maliciosas. |
| `requests` | 2.32.4 | HTTP client | Usado para llamadas a OpenLibrary API. 2.32.x corrige CVE-2024-35195 y CVE-2024-47081. |
| `feedparser` | 6.0.11 | Parser de RSS/Atom | Usado para sincronización del feed de Goodreads. Tolerante a feeds malformados. |
| `beautifulsoup4` | 4.12.3 | Parser de HTML | Usado en el scraper de Goodreads para parsear tablas HTML externas. |
| `onnxruntime` | 1.20.1 | Runtime de modelos ONNX | Ejecuta el modelo de embeddings sin PyTorch. ~50ms por texto en CPU. Ver [ADR 0003](../adr/0003-onnx-runtime-local.md). |
| `numpy` | 1.26.4 | Operaciones vectoriales | Requerido por onnxruntime. Pinado a 1.26.x por compatibilidad con la API de numpy arrays. |
| `scikit-learn` | 1.5.2 | ML para clustering y moderación | Usado en el motor de moderación de comentarios y para clustering de afinidad. |
| `tokenizers` | 0.21.0 | Tokenización ONNX | Librería de Hugging Face en Rust para tokenizar texto antes de pasarlo al modelo ONNX. Liviana: no requiere PyTorch. |
| `python-dateutil` | 2.9.0 | Parsing robusto de fechas | Usado en parsers de importación donde las fechas vienen en formatos variables. |
| `sentry-sdk` | 2.19.2 | Observabilidad y error tracking | Integración con Django y Celery. Solo activo si `SENTRY_DSN` está configurado. |
| `gunicorn` | 23.0.0 | WSGI server de producción | Worker class `gthread` (multithread). 4 workers × 2 threads = 8 requests concurrentes por defecto. |
| `coverage` | 7.6.10 | Medición de cobertura de tests | Usado en CI para verificar que la cobertura no baje del 60%. |

---

## Gestión de versiones

Las versiones están pinadas en `requirements.txt`. Para actualizarlas:

```bash
# Instalar pip-tools si no está disponible
pip install pip-tools

# Compilar requirements.in a requirements.txt con versiones actualizadas
pip-compile requirements.in

# Verificar que no haya CVEs nuevos
pip-audit -r requirements.txt
```

Si `requirements.in` no existe, las versiones se actualizan editando `requirements.txt` manualmente y corriendo `pip-audit` para verificar.
