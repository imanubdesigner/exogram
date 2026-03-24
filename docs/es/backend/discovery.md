# App: discovery

Descubrimiento de usuarios, libros y highlights afines dentro de la red.

---

## Propósito

El módulo de discovery conecta a los lectores entre sí a partir de sus afinidades literarias.
No es un feed algorítmico abierto: el descubrimiento está acotado a la red de cada usuario.

---

## Funcionalidades

### Búsqueda semántica de highlights

`POST /api/discovery/search/`

```json
{
  "query": "el tiempo como constructor de identidad",
  "scope": "mine",
  "limit": 10
}
```

- `scope=mine`: busca entre los propios highlights del usuario.
- `scope=network`: busca entre highlights públicos de usuarios en su red.

Internamente convierte el query a embedding ONNX y ejecuta una búsqueda por distancia coseno en pgvector.

### Usuarios con afinidad similar

Usa los centroides de `UserCluster` para encontrar usuarios cuyo perfil lector
(promedio de embeddings de sus highlights) es más cercano al del usuario actual.

### Libros en común

Descubre qué libros tiene el usuario en común con otros lectores de su red,
potencial punto de partida para un `Thread`.

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| POST | `/api/discovery/search/` | Búsqueda semántica de highlights |
| GET | `/api/discovery/users/` | Usuarios con afinidad lectora similar |
| GET | `/api/discovery/books/` | Libros comunes con usuarios de la red |
