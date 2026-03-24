# 0008 — Django 5.2 LTS

## Context

When the project started, Django 5.x was the current version. A choice had to be made
between an LTS version and a standard version.

## Decision

Use Django 5.2 LTS. Security support guaranteed until April 2028.

## Alternatives considered

**Django 5.0 / 5.1 (standard versions):** support cycle of ~16 months.
Django 5.0 reached EOL in April 2025. For a project aimed at long-term production,
non-LTS versions imply frequent forced migrations.

**Django 4.2 LTS:** previous version with support until April 2026. Discarded to
avoid reaching EOL in the short term and to take advantage of the improvements in Django 5.x.

## Consequences

- No pressure to upgrade the major version until 2028.
- Guaranteed compatibility with djangorestframework 3.15.x, simplejwt 5.x, and django-celery-beat 2.x during the support cycle.
- In 2027-2028, evaluate migration to the next LTS version (likely Django 6.2 LTS).
