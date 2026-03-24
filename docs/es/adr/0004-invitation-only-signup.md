# 0004 — Registro solo por invitación


## Contexto

Exogram es una red social de lectores con un enfoque deliberadamente curado.
La calidad de la comunidad y la confianza entre usuarios son parte central del producto.
El registro abierto podría degradar esa calidad e introducir spam o comportamientos
incompatibles con la cultura del proyecto.

## Decisión

El único camino para crear una cuenta es ser invitado por un usuario existente o
ser activado desde la lista de espera (waitlist) por un usuario con invitaciones disponibles.

**Flujo de invitación:**
1. Un usuario registrado envía una invitación a un email.
2. El sistema genera un token HMAC-SHA256 (con `SECRET_KEY` como clave) y lo envía por email.
3. El invitado usa el link para completar el registro dentro de 72 horas.
4. Al registrarse, el invitado queda asociado al invitante en el grafo de red.

**Waitlist:**
1. Cualquier persona puede anotarse en la lista de espera con su email.
2. Un usuario registrado puede activar a alguien de la waitlist, consumiendo una invitación.

**Límites:**
- Cada usuario tiene un número máximo de invitaciones (`MAX_INVITATIONS_PER_USER = 10`).
- Los tokens de invitación expiran a los 72 horas (`token_created_at` + 72h).
- Los tokens usan HMAC en lugar de SHA256 sin sal para resistir ataques de rainbow table.

**Sistema de confianza (trust levels):**
Los usuarios nuevos entran con `comment_allowance_depth = 0`. A los 30 días se promueven
automáticamente a `depth = 1` vía tarea Celery diaria. Este nivel controla qué tan lejos
en el grafo social pueden interactuar.

## Alternativas consideradas

**Registro abierto:** más fácil para crecer, pero contradice el diseño intencional del
producto. Exogram no es una red para todos, es una red para lectores comprometidos.

**Registro por invitación sin waitlist:** deja afuera a personas interesadas que no
conocen a un usuario. La waitlist es la válvula: permite capturar interés y activar
usuarios con control.

## Consecuencias

- El crecimiento es lento por diseño. Esto es intencional.
- Los usuarios tienen incentivo a invitar personas de calidad (su reputación en el grafo está asociada a sus invitados).
- El sistema de trust levels permite moderar la participación de usuarios nuevos sin intervención manual.
- La expiración de 72h requiere que el email sea funcional. No hay forma de recuperar una invitación expirada sin que el invitante genere una nueva.
