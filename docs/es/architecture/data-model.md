# Modelo de datos

Entidades principales y sus relaciones. Sin DDL: para el schema exacto, ver las migraciones.

---

## Diagrama de entidades

```
User (Django built-in)
 │ OneToOne
 ▼
Profile ──────────────────────────────────────────────────────────┐
 │ nickname, bio, avatar, verified_email                          │
 │ is_hermit_mode, comment_allowance_depth                       │
 │ invitations_remaining, trust_promoted_at                      │
 │                                                               │
 ├── OneToOne ──► UserCluster (centroid vector 384d)             │
 │                                                               │
 ├── FK (invited_by) ──► Invitation                              │
 │     email, token_hash (HMAC), token_created_at, expires_at   │
 │     accepted_at                                               │
 │                                                               │
 ├── FK ──► Waitlist                                             │
 │     email, message, activated_at, activated_by               │
 │                                                               │
 ├── FK ──► PasswordResetToken                                   │
 │     token_hash, expires_at, used_at                          │
 │                                                               │
 ├── FK ──► ReadingSession                                       │
 │     book, status, started_at, finished_at, rating            │
 │                                                               │
 ├── FK (user) ──► Highlight                                     │
 │     book, content, note, location                            │
 │     visibility (private|unlisted|public)                     │
 │     embedding (VectorField 384d, nullable)                   │
 │     is_favorite                                              │
 │      │                                                        │
 │      │ FK (highlight) ──► Comment                            │
 │      │     author (Profile), content                         │
 │      │     moderation_score, moderation_reason, is_hidden    │
 │      │                                                        │
 │      └── FK (book) ──► Book                                  │
 │              title, isbn (unique), cover_image               │
 │              openlibrary_id, average_rating                  │
 │              publish_year, genre                             │
 │               │                                              │
 │               └── ManyToMany ──► Author                      │
 │                       name, openlibrary_id                   │
 │                                                              │
 ├── ManyToMany (participants) ──► Thread                       │
 │     context_book_title, last_message_at                      │
 │      │                                                       │
 │      └── FK (thread) ──► ThreadMessage                       │
 │              author (Profile), content                       │
 │                                                              │
 └── FK (follower/following) ──► UserFollow                     │
       created_at                                               │
                                                               │
Article ─────────────────────────────────────────────────────── ┘
  title, slug, content, published_at, is_published
  (contenido editorial del proyecto, independiente de los usuarios)
```

---

## Notas sobre el diseño

**Profile como entidad central.** Casi todas las relaciones van a `Profile`, no a `User`.
`User` es el modelo de autenticación de Django (username, password, email).
`Profile` es la identidad de Exogram (nickname, bio, trust level, etc.).
Están vinculados OneToOne y se crean juntos vía señal `post_save`.

**Highlight es el objeto central del negocio.** Todo gira alrededor del highlight:
se importa, se anota, se vectoriza, se comenta, se comparte. El `embedding` nullable
es clave: se crea sin embedding y lo recibe de forma asíncrona.

**Tokens nunca se almacenan en claro.** `Invitation.token_hash` y `PasswordResetToken.token_hash`
almacenan HMAC-SHA256 del token raw. El token raw solo existe en el email enviado al destinatario.

**VectorField** en `Highlight.embedding` y `UserCluster.centroid`.
`Highlight.embedding` tiene índice HNSW para búsqueda aproximada eficiente.
`UserCluster.centroid` no tiene índice (se usa para comparación directa entre pocos usuarios).

**Thread siempre tiene exactamente dos participantes.** No hay grupos. El diseño es deliberado:
los hilos son entre dos lectores, como una conversación privada a partir de un libro en común.

---

## Volúmenes esperados en producción temprana

| Entidad | Orden de magnitud esperado |
|---|---|
| Usuarios | Cientos |
| Highlights por usuario | Cientos a miles |
| Embeddings (384 floats × 4 bytes) | ~1.5 KB por highlight |
| Tamaño de la tabla highlights (10k highlights) | ~15 MB en vectores + overhead |
| Centroides de UserCluster | 1 por usuario, despreciable |

pgvector con índice HNSW maneja cómodamente millones de vectores. Para el volumen
inicial el índice es innecesario pero no perjudicial.
