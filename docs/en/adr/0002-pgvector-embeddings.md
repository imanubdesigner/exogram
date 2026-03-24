# 0002 — pgvector as vector store instead of a dedicated service

## Context

The semantic search functionality for highlights requires storing and querying
384-dimensional embedding vectors. There are dedicated services for this
(Pinecone, Weaviate, Qdrant, Milvus) as well as the `pgvector` extension for PostgreSQL.

## Decision

Use `pgvector` as a PostgreSQL extension. Embeddings are stored as `VectorField`
columns in Django models alongside the rest of the data.

Similarity search uses pgvector's cosine distance function:
```sql
SELECT * FROM books_highlight
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

## Alternatives considered

**Pinecone / Weaviate / Qdrant:** specialized services with better performance at
million-scale. They require another service in the stack (operational cost, network latency,
another point of failure, extra authentication). For the project's current volume
(personal highlights per user, on the order of thousands to tens of thousands per user)
pgvector's performance is more than sufficient.

**Elasticsearch with dense vectors:** more infrastructure, higher RAM consumption,
high operational complexity for a small team.

## Consequences

- The stack stays on a single datastore (PostgreSQL). No synchronization between systems.
- Django migrations manage the vector schema just like any other field.
- The custom test runner (`PgVectorTestRunner`) enables the `vector` extension in the test database before migrating, which resolves the `type "vector" does not exist` error in CI.
- If the volume grows to tens of millions of vectors, migrating to a dedicated vector store is the natural path. pgvector can be scaled with HNSW or IVFFlat indexes before reaching that point.
- The base Docker image uses `pgvector/pgvector:pg16` instead of `postgres:16` to have the extension available in CI and dev.
