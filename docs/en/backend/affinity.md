# App: affinity

User clustering by reading affinity and reading session tracking.

---

## Models

### `UserCluster`

Represents a user's position in the reading affinity space.

- `profile` → OneToOne with `Profile`
- `centroid` — `VectorField(dimensions=384)`. Average of the user's highlight embeddings. Represents their reading "center of gravity".
- `updated_at`

### `ReadingSession`

Record of a user's reading session (a book that is being read, finished, or on the wishlist).

- `profile` → FK to `Profile`
- `book` → FK to `Book`
- `status`: `reading` | `finished` | `want_to_read`
- `started_at`, `finished_at`
- `rating` — personal rating (nullable)

---

## Clustering

### `compute_user_centroid(profile) -> ndarray`

Calculates the user's centroid by averaging the embeddings of all their highlights
that have a generated embedding. If the user has no highlights with an embedding, returns `None`.

### `update_user_cluster(profile)`

Calls `compute_user_centroid` and updates (or creates) the user's `UserCluster`.
Called after processing a batch of embeddings.

---

## Centroid usage

The `UserCluster` centroid is used in the discovery module to find users
with similar reading affinity: the cosine distance between different users'
centroids is compared to suggest potential connections.

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/api/affinity/graph/` | User's network graph (nodes and edges) |
| GET | `/api/affinity/similar/` | Users with similar reading affinity |
| POST | `/api/reading-sessions/` | Record a reading session |
| PATCH | `/api/reading-sessions/<id>/` | Update reading status |
