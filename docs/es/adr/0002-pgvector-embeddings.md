# 0002 — pgvector como vector store en lugar de servicio dedicado


## Contexto

La funcionalidad de búsqueda semántica de highlights requiere almacenar y consultar
vectores de embeddings de 384 dimensiones. Existen servicios dedicados para esto
(Pinecone, Weaviate, Qdrant, Milvus) y también la extensión `pgvector` para PostgreSQL.

## Decisión

Usar `pgvector` como extensión de PostgreSQL. Los embeddings se almacenan como columnas
`VectorField` en los modelos Django junto al resto de los datos.

La búsqueda de similitud usa la función de distancia coseno de pgvector:
```sql
SELECT * FROM books_highlight
ORDER BY embedding <=> query_embedding
LIMIT 10;
```

## Alternativas consideradas

**Pinecone / Weaviate / Qdrant:** servicios especializados con mejor rendimiento a
escala millonaria. Requieren otro servicio en el stack (costo operacional, latencia de red,
otro punto de falla, autenticación extra). Para el volumen actual del proyecto
(highlights personales de cada usuario, del orden de miles a decenas de miles por usuario)
el rendimiento de pgvector es más que suficiente.

**Elasticsearch con dense vectors:** más infraestructura, mayor consumo de RAM,
complejidad operacional alta para un equipo pequeño.

## Consecuencias

- El stack se mantiene en un único datastore (PostgreSQL). Sin sincronización entre sistemas.
- Las migraciones de Django gestionan el schema de los vectores igual que cualquier otro campo.
- El test runner custom (`PgVectorTestRunner`) habilita la extensión `vector` en la base de tests antes de migrar, lo que resuelve el error `type "vector" does not exist` en CI.
- Si el volumen crece a decenas de millones de vectores, migrar a un vector store dedicado es el camino natural. pgvector puede escalarse con índices HNSW o IVFFlat antes de llegar a ese punto.
- La imagen Docker base usa `pgvector/pgvector:pg16` en lugar de `postgres:16` para tener la extensión disponible en CI y en dev.
