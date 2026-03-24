# Estrategia de tests

---

## Filosofía

**Integración sobre unitarios.**

La mayoría de los tests en Exogram hacen requests HTTP a los endpoints reales y verifican
el comportamiento end-to-end: autenticación, validaciones, respuestas, efectos en la base de datos.
No se mockea la base de datos ni el ORM.

Esto tiene un costo (los tests son más lentos que tests unitarios puros) y un beneficio:
los tests son fieles al comportamiento real. Un test que pasa con la DB real es más confiable
que uno que pasa con un mock que podría divergir del comportamiento real.

---

## Infraestructura de tests

### Base de datos

Los tests usan una base de datos PostgreSQL real (en CI, levantada como servicio en el job).
El test runner `PgVectorTestRunner` habilita la extensión `vector` antes de migrar,
lo que permite testear modelos con `VectorField` sin configuración adicional.

### Password hashing

`settings_ci.py` configura `FastPBKDF2PasswordHasher` (iterations=1) para que la creación
de usuarios en tests sea rápida (<1ms vs ~100ms con el hasher de producción).

### Throttling

`settings_ci.py` desactiva el throttling global para evitar falsos negativos en tests que
hacen muchos requests seguidos. Los tests de throttling específicos deben usar
`override_settings` para restaurar los throttles en ese test puntual.

---

## Cobertura

El CI verifica que la cobertura no baje del **60%** con `coverage --fail-under=60`.

Este umbral es conservador por diseño: mejor tener un umbral alcanzable y subir
la exigencia con el tiempo que bloquear el CI con un umbral arbitrariamente alto.

Para ver el reporte de cobertura localmente:

```bash
coverage run --source='.' manage.py test
coverage report
coverage html   # genera htmlcov/ con visualización por archivo
```

---

## Qué se testea

- **accounts:** todos los flujos de autenticación, perfil, avatar, invitaciones, waitlist.
- **books:** importación, parsers, modelos, export, Goodreads, public notes, auth views.
- **social:** moderación automática de comentarios, puntajes de toxicidad.
- **threads:** CRUD de hilos y mensajes, restricciones de red.
- **affinity:** clustering, modelos.
- **frontend:** auth store, router guard, resolución de URL de la API.

## Qué no se testea (y por qué)

- **Tareas Celery:** las tareas se testean indirectamente a través de las vistas que las disparan. El comportamiento interno de Celery (retry, backoff) no se testa: es responsabilidad de Celery, no de la aplicación.
- **Migraciones:** Django garantiza que las migraciones son consistentes con `manage.py makemigrations --check` en CI.
- **Código de scraping de HTML externo (`goodreads_reading_scraper.py`):** el HTML de Goodreads cambia sin aviso. El código tiene excepciones tolerantes por diseño y está marcado con `# pragma: no cover` en los bloques que dependen de estructura HTML externa.
- **Smoke tests (`smoke_tests/`):** están excluidos del runner principal. Son tests de integración contra una instancia real y se corren manualmente antes de un deploy crítico.
