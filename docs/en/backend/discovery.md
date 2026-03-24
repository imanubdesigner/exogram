# App: discovery

Discovery of users, books, and highlights with affinity within the network.

---

## Purpose

The discovery module connects readers with each other based on their literary affinities.
It is not an open algorithmic feed: discovery is scoped to each user's network.

---

## Features

### Semantic highlight search

`POST /api/discovery/search/`

```json
{
  "query": "el tiempo como constructor de identidad",
  "scope": "mine",
  "limit": 10
}
```

- `scope=mine`: searches among the user's own highlights.
- `scope=network`: searches among public highlights from users in their network.

Internally converts the query to an ONNX embedding and executes a cosine distance search in pgvector.

### Users with similar affinity

Uses `UserCluster` centroids to find users whose reading profile
(average of their highlights' embeddings) is closest to the current user's.

### Books in common

Discovers which books the user shares with other readers in their network,
a potential starting point for a `Thread`.

---

## Endpoints

| Method | URL | Description |
|---|---|---|
| POST | `/api/discovery/search/` | Semantic highlight search |
| GET | `/api/discovery/users/` | Users with similar reading affinity |
| GET | `/api/discovery/books/` | Books in common with network users |
