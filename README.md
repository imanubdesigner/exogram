<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-banner-dark.png" />
    <img src="assets/logo-banner-light.png" alt="Exogram" width="400" />
  </picture>
</p>

<p align="center">
  <a href="https://github.com/matzalazar/exogram/actions/workflows/ci.yml">
    <img src="https://github.com/matzalazar/exogram/actions/workflows/ci.yml/badge.svg" alt="CI" />
  </a>
  <img src="https://img.shields.io/badge/python-3.12-blue" alt="Python 3.12" />
  <img src="https://img.shields.io/badge/django-5.2%20LTS-092E20" alt="Django 5.2 LTS" />
  <img src="https://img.shields.io/badge/node-20-339933" alt="Node 20" />
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-AGPL--3.0-blue" alt="License" />
  </a>
</p>

<p align="center">A social network for readers.</p>

---

## What is Exogram

Exogram is a place to save your book highlights and notes, and from there find other people who read in a similar way to you.

No engagement algorithms. No like counts. No infinite scroll. 

Just **readers** and what they underline.

---

## What you can do

**Save your library**  
- Import your highlights from Kindle. Each highlight is stored with its personal note, the book it belongs to, and its location in the text.

**Find like-minded readers**  
- Exogram analyzes your highlights to understand what topics interest you and connects you with people who underlined similar things — even across different books.

**Explore ideas**  
- Search for a concept and the system finds highlights from your library — or from the network — that talk about the same thing, even without using the same words.

**Talk to readers nearby**  
- Start a private thread with someone in your network based on a book you have in common. No public exposure, no large groups.

**Control your privacy**  
- Your notes are yours. You choose which highlights are public, which are private, and which are hidden but accessible by link. If you prefer to go unnoticed, hermit mode makes you invisible to the rest of the network.

---

## How to join

Exogram is invitation-only. To join you need someone already on the network to invite you by email, or you can sign up for the waitlist.

If someone sent you an invitation, the link in the email takes you directly to the registration flow.

---

## For developers

Technical documentation is available in English and Spanish → [`docs/`](./docs/)

**English** · [`docs/en/`](./docs/en/)

- [Local development](./docs/en/operations/local-development.md) — how to run the project locally
- [Environment variables](./docs/en/operations/environment-variables.md) — full configuration reference
- [Production deploy](./docs/en/operations/deployment.md) — CI/CD flow and server setup
- [Operational runbook](./docs/en/operations/runbook.md) — procedures for production incidents
- [Backend apps](./docs/en/backend/) — documentation for each Django app
- [Architecture decisions](./docs/en/adr/) — the reasoning behind key technical choices
- [Security](./docs/en/security/) — implemented controls and threat model
- [Tests](./docs/en/testing/) — strategy and coverage

**Español** · [`docs/es/`](./docs/es/)

- [Desarrollo local](./docs/es/operations/local-development.md) — cómo levantar el proyecto en tu máquina
- [Variables de entorno](./docs/es/operations/environment-variables.md) — referencia completa de configuración
- [Deploy a producción](./docs/es/operations/deployment.md) — flujo CI/CD y configuración del servidor
- [Runbook operacional](./docs/es/operations/runbook.md) — procedimientos para situaciones en producción
- [Apps del backend](./docs/es/backend/) — documentación de cada app Django
- [Decisiones de arquitectura](./docs/es/adr/) — el por qué de las decisiones técnicas importantes
- [Seguridad](./docs/es/security/) — controles implementados y modelo de amenazas
- [Tests](./docs/es/testing/) — estrategia y cobertura

---

## License

See [LICENSE](LICENSE).
