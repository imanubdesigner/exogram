# Data Model

Main entities and their relationships. No DDL: for the exact schema, see the migrations.

---

## Entity diagram

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
  (editorial content of the project, independent of users)
```

---

## Design notes

**Profile as the central entity.** Almost all relationships point to `Profile`, not to `User`.
`User` is Django's authentication model (username, password, email).
`Profile` is the Exogram identity (nickname, bio, trust level, etc.).
They are linked OneToOne and created together via a `post_save` signal.

**Highlight is the core business object.** Everything revolves around the highlight:
it is imported, annotated, vectorized, commented on, and shared. The nullable `embedding`
is key: a highlight is created without an embedding and receives it asynchronously.

**Tokens are never stored in plaintext.** `Invitation.token_hash` and `PasswordResetToken.token_hash`
store the HMAC-SHA256 of the raw token. The raw token only exists in the email sent to the recipient.

**VectorField** on `Highlight.embedding` and `UserCluster.centroid`.
`Highlight.embedding` has an HNSW index for efficient approximate search.
`UserCluster.centroid` has no index (used for direct comparison among a small number of users).

**Thread always has exactly two participants.** There are no groups. The design is deliberate:
threads are between two readers, like a private conversation sparked by a book in common.

---

## Expected volumes in early production

| Entity | Expected order of magnitude |
|---|---|
| Users | Hundreds |
| Highlights per user | Hundreds to thousands |
| Embeddings (384 floats × 4 bytes) | ~1.5 KB per highlight |
| Size of the highlights table (10k highlights) | ~15 MB in vectors + overhead |
| UserCluster centroids | 1 per user, negligible |

pgvector with an HNSW index comfortably handles millions of vectors. For the
initial volume the index is unnecessary but not harmful.
