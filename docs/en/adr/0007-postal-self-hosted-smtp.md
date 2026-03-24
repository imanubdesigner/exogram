# 0007 — Postal as a self-hosted SMTP server

## Context

The system needs to send transactional emails: invitations, password resets.
A reliable SMTP server is required.

## Decision

Use Postal (https://postalserver.io) self-hosted, included in the Docker stack as
a service with the `mail` profile. Postal uses MariaDB as its store and Redis as its internal broker.

## Alternatives considered

**SendGrid / Mailgun / Amazon SES:** managed services with high deliverability,
no infrastructure to maintain, but with volume-based costs and user emails
processed by a third party. For a privacy-focused project like Exogram, sending emails
through a third party contradicts the spirit of the product.

**Postfix directly:** lighter than Postal, but without an administration interface,
without delivery metrics, and difficult to configure correctly (SPF, DKIM, DMARC).

**Gmail/Outlook SMTP:** useful for development, not scalable for transactional production.

## Consequences

- Emails never leave the project's own stack. Full control over the data.
- Postal requires DNS configuration (SPF, DKIM, PTR/rDNS) for good deliverability. Without this configuration, emails may go to spam.
- Port 25 (SMTP) and 587 (submission) are exposed in production. With some cloud providers (Hetzner included) port 25 may be blocked by default and requires explicit approval.
- Postal is in the stack as the `mail` profile (`docker compose --profile mail up`). It does not start by default in development to avoid unnecessarily loading the local environment.
- For development, `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` prints emails in the logs without needing Postal.
