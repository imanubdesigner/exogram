# App: social

Comentarios en highlights y sistema de seguimiento entre usuarios.

---

## Modelos

### `Comment`

Comentario en un highlight público.

- `highlight` → FK a `Highlight`
- `author` → FK a `Profile`
- `content` — texto del comentario
- `created_at`
- `moderation_score` — puntuación de toxicidad asignada automáticamente (0.0–1.0)
- `moderation_reason` — razón textual si fue moderado
- `is_hidden` — si `True`, el comentario no es visible. Resultado de moderación automática.

### `UserFollow`

Relación de seguimiento entre usuarios.

- `follower` → FK a `Profile`
- `following` → FK a `Profile`
- `created_at`
- Constraint único: un usuario no puede seguir al mismo usuario dos veces.

---

## Moderación automática

### `analyze_toxicity(text) -> (score: float, reason: str)`

Motor de moderación local sin dependencias externas ni APIs. Combina:

1. **Lista de palabras tóxicas** ponderadas: insultos comunes en español con pesos distintos según severidad.
2. **Detección de spam**: URLs múltiples (≥ 3 en el mismo mensaje) aumentan el score.
3. **CAPS abuse**: porcentaje alto de mayúsculas sobre texto largo eleva el score.
4. **Repetición**: caracteres repetidos excesivamente ("jajajajajaja") como señal de ruido.

El score resultante es un float entre 0 y 1. Los umbrales se aplican en `moderate_comment`.

### `moderate_comment(comment) -> Comment`

Llama a `analyze_toxicity`, asigna `moderation_score` y `moderation_reason`.
Si el score supera el umbral configurado, pone `is_hidden=True` automáticamente.
Los comentarios ocultos quedan registrados pero no se devuelven en la API.

---

## Restricciones de red

Los comentarios no son abiertos a cualquiera. La función `are_in_same_network(profile_a, profile_b)`
(en `accounts/utils.py`) verifica que los dos usuarios estén dentro de la distancia de red
permitida por el sistema de trust levels.

Un usuario con `comment_allowance_depth=0` solo puede interactuar con usuarios a distancia 0
en el grafo de red (en la práctica, solo puede ver pero no comentar hasta ser promovido).
Un usuario con `depth=1` puede comentar en highlights de usuarios que están dentro de su red.

---

## Endpoints

| Método | URL | Descripción |
|---|---|---|
| GET | `/api/highlights/<id>/comments/` | Listar comentarios de un highlight |
| POST | `/api/highlights/<id>/comments/` | Crear comentario (con moderación automática) |
| DELETE | `/api/comments/<id>/` | Borrar comentario propio |
| POST | `/api/users/<nickname>/follow/` | Seguir a un usuario |
| DELETE | `/api/users/<nickname>/follow/` | Dejar de seguir |
| GET | `/api/me/following/` | Usuarios que sigo |
| GET | `/api/me/followers/` | Usuarios que me siguen |
