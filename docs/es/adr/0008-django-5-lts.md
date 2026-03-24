# 0008 — Django 5.2 LTS


## Contexto

Al iniciar el proyecto, Django 5.x era la versión actual. Se debía elegir entre
una versión LTS y una versión estándar.

## Decisión

Usar Django 5.2 LTS. Soporte de seguridad garantizado hasta abril de 2028.

## Alternativas consideradas

**Django 5.0 / 5.1 (versiones estándar):** ciclo de soporte de ~16 meses.
Django 5.0 llegó a EOL en abril 2025. Para un proyecto que apunta a producción
de largo plazo, las versiones no-LTS implican migraciones forzadas frecuentes.

**Django 4.2 LTS:** versión anterior con soporte hasta abril 2026. Descartado para
no quedar en EOL a corto plazo y poder aprovechar las mejoras de Django 5.x.

## Consecuencias

- Sin presión de actualización de versión mayor hasta 2028.
- Compatibilidad garantizada con djangorestframework 3.15.x, simplejwt 5.x y django-celery-beat 2.x durante el ciclo de soporte.
- En 2027-2028 evaluar migración a la siguiente versión LTS (probablemente Django 6.2 LTS).
