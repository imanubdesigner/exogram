# App: affinity

Clustering de usuarios por afinidad lectora y registro de sesiones de lectura.

---

## Modelos

### `UserCluster`

Representa la posición de un usuario en el espacio de afinidad lectora.

- `profile` → OneToOne con `Profile`
- `centroid` — `VectorField(dimensions=384)`. Promedio de los embeddings de los highlights del usuario. Representa su "centro de gravedad" lector.
- `updated_at`

### `ReadingSession`

Registro de una sesión de lectura de un usuario (un libro leído, en proceso, o en wishlist).

- `profile` → FK a `Profile`
- `book` → FK a `Book`
- `status`: `reading` | `finished` | `want_to_read`
- `started_at`, `finished_at`
- `rating` — calificación personal (nullable)

---

## Clustering

### `compute_user_centroid(profile) -> ndarray`

Calcula el centroide del usuario promediando los embeddings de todos sus highlights
que tengan embedding generado. Si el usuario no tiene highlights con embedding, devuelve `None`.

### `update_user_cluster(profile)`

Llama a `compute_user_centroid` y actualiza (o crea) el `UserCluster` del usuario.
Se llama después de procesar un batch de embeddings.

---

## Uso del centroide

El centroide de `UserCluster` se usa en el módulo de discovery para encontrar usuarios
con afinidad lectora similar: se compara la distancia coseno entre centroides de distintos
usuarios para sugerir conexiones potenciales.

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/affinity/graph/` | Grafo de red del usuario (nodos y aristas) |
| GET | `/api/affinity/similar/` | Usuarios con afinidad lectora similar |
| POST | `/api/reading-sessions/` | Registrar sesión de lectura |
| PATCH | `/api/reading-sessions/<id>/` | Actualizar estado de lectura |
