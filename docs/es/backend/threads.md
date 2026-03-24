# App: threads

Hilos de mensajería privada entre lectores afines.

---

## Modelos

### `Thread`

Hilo de conversación entre dos usuarios.

- `participants` — ManyToMany con `Profile` (siempre exactamente 2)
- `context_book_title` — título del libro que motivó el contacto (opcional, informativo)
- `last_message_at` — timestamp del último mensaje, actualizado en cada envío
- `created_at`

Método `get_other_participant(my_profile)`: devuelve el otro participante del hilo.

### `ThreadMessage`

Mensaje dentro de un hilo.

- `thread` → FK a `Thread`
- `author` → FK a `Profile`
- `content` — texto del mensaje
- `created_at`

---

## Restricciones

Solo se puede iniciar un hilo entre dos usuarios si ambos están dentro de la **distancia de red permitida** (`are_in_same_network`). Esto previene mensajes no solicitados desde usuarios fuera de la red del destinatario.

Si ya existe un hilo entre dos usuarios y se intenta crear uno nuevo, el endpoint devuelve el hilo existente (idempotente).

---

## Optimización N+1

La vista de lista de hilos (`ThreadListCreateView`) usa `Prefetch` para pre-cargar
el último mensaje de cada hilo en una sola query:

```python
Thread.objects.prefetch_related(
    Prefetch('messages', queryset=ThreadMessage.objects.order_by('-created_at')[:1],
             to_attr='prefetched_messages')
)
```

El serializador `_serialize_thread` usa el atributo `prefetched_messages` si está disponible,
evitando una query adicional por hilo.

---

## Paginación de mensajes

`GET /api/threads/<id>/messages/` devuelve los últimos 50 mensajes del hilo, ordenados cronológicamente.
Soporta cursor de paginación hacia atrás con el parámetro `before=<message_id>` para cargar mensajes más antiguos.

---

## Rate limiting en polling

El frontend puede hacer polling periódico para nuevos mensajes. Para evitar que esto consuma
el límite global de requests, los endpoints de mensajes usan el throttle scope `chat_polling`
(2000 requests/hora en producción, prácticamente ilimitado en CI).

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/threads/` | Listar mis hilos |
| POST | `/api/threads/` | Crear hilo con otro usuario |
| GET | `/api/threads/<id>/` | Detalle de un hilo + últimos mensajes |
| POST | `/api/threads/<id>/messages/` | Enviar mensaje en un hilo |
| GET | `/api/threads/<id>/messages/` | Listar mensajes (con paginación por cursor) |
