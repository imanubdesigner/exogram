# 0007 — Postal como servidor SMTP self-hosted


## Contexto

El sistema necesita enviar emails transaccionales: invitaciones, reset de contraseña.
Se necesita un servidor SMTP confiable.

## Decisión

Usar Postal (https://postalserver.io) self-hosted, incluido en el stack Docker como
servicio con profile `mail`. Postal usa MariaDB como almacén y Redis como broker interno.

## Alternativas consideradas

**SendGrid / Mailgun / Amazon SES:** servicios gestionados con alta deliverability,
sin infraestructura que mantener, pero con costo por volumen y los emails de los usuarios
procesados por un tercero. Para un proyecto de privacidad como Exogram, enviar emails
a través de un tercero contradice el espíritu del producto.

**Postfix directo:** más liviano que Postal, pero sin interfaz de administración,
sin métricas de entrega y difícil de configurar correctamente (SPF, DKIM, DMARC).

**SMTP de Gmail/Outlook:** útil para desarrollo, no escalable para producción transaccional.

## Consecuencias

- Los emails nunca salen del stack propio. Control total sobre los datos.
- Postal requiere configuración de DNS (SPF, DKIM, PTR/rDNS) para buena deliverability. Sin esta configuración los emails pueden ir a spam.
- El puerto 25 (SMTP) y 587 (submission) se exponen en producción. En algunos proveedores de cloud (Hetzner incluido) el puerto 25 puede estar bloqueado por defecto y requiere aprobación explícita.
- Postal está en el stack como profile `mail` (`docker compose --profile mail up`). No levanta por defecto en desarrollo para no cargar innecesariamente el entorno local.
- Para desarrollo, `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` imprime los emails en los logs sin necesidad de Postal.
