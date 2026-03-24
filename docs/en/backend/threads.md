# App: threads

Private messaging threads between like-minded readers.

---

## Models

### `Thread`

Conversation thread between two users.

- `participants` — ManyToMany with `Profile` (always exactly 2)
- `context_book_title` — title of the book that motivated the contact (optional, informational)
- `last_message_at` — timestamp of the last message, updated on each send
- `created_at`

Method `get_other_participant(my_profile)`: returns the other participant in the thread.

### `ThreadMessage`

Message within a thread.

- `thread` → FK to `Thread`
- `author` → FK to `Profile`
- `content` — message text
- `created_at`

---

## Restrictions

A thread can only be started between two users if both are within the **allowed network distance** (`are_in_same_network`). This prevents unsolicited messages from users outside the recipient's network.

If a thread already exists between two users and a new one is attempted, the endpoint returns the existing thread (idempotent).

---

## N+1 optimization

The thread list view (`ThreadListCreateView`) uses `Prefetch` to pre-load
the last message of each thread in a single query:

```python
Thread.objects.prefetch_related(
    Prefetch('messages', queryset=ThreadMessage.objects.order_by('-created_at')[:1],
             to_attr='prefetched_messages')
)
```

The `_serialize_thread` serializer uses the `prefetched_messages` attribute when available,
avoiding an additional query per thread.

---

## Message pagination

`GET /api/threads/<id>/messages/` returns the last 50 messages in the thread, ordered chronologically.
Supports backward cursor pagination with the `before=<message_id>` parameter to load older messages.

---

## Rate limiting on polling

The frontend can perform periodic polling for new messages. To prevent this from consuming
the global request limit, message endpoints use the `chat_polling` throttle scope
(2000 requests/hour in production, practically unlimited in CI).

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/api/threads/` | List my threads |
| POST | `/api/threads/` | Create a thread with another user |
| GET | `/api/threads/<id>/` | Thread detail + latest messages |
| POST | `/api/threads/<id>/messages/` | Send a message in a thread |
| GET | `/api/threads/<id>/messages/` | List messages (with cursor pagination) |
