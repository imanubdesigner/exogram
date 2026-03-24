# Scanning de seguridad en CI

El CI ejecuta tres herramientas de análisis de seguridad en cada push.

---

## bandit — Análisis estático (SAST)

**Job:** `backend-lint`
**Comando:** `bandit -r . -x ./migrations,./smoke_tests -ll -ii -c .bandit`

Analiza el código Python en busca de patrones inseguros comunes: uso de `eval`,
subprocesos con shell=True, credenciales hardcodeadas, uso de funciones criptográficas débiles, etc.

**Flags usados:**
- `-ll`: reporta solo issues de severidad LOW o superior (incluye todos).
- `-ii`: reporta solo issues de confianza MEDIUM o superior (filtra falsos positivos obvios).
- `-c .bandit`: lee la configuración desde `backend/.bandit`.

**Configuración `.bandit`:**
```ini
skips: ['B101', 'B311']
```
- `B101` (uso de `assert`): falso positivo esperado en tests. `assert` en tests es correcto.
- `B311` (uso de `random`): en este proyecto `random` no se usa para criptografía, solo para lógica de aplicación. Los tokens y secrets usan `secrets` de stdlib.

---

## pip-audit — Vulnerabilidades en dependencias

**Job:** `backend-lint`
**Comando:** `pip-audit -r requirements.txt`

Consulta la base de datos de PyPA (OSV) para detectar CVEs conocidos en las dependencias
de Python declaradas en `requirements.txt`. No requiere autenticación ni API key.

Reemplaza a `safety` (que requirió autenticación a partir de la versión 2.3.5).

Si encuentra vulnerabilidades con severidad CRITICAL o HIGH, el job falla y bloquea el merge.

**Acción ante una alerta:** actualizar el paquete afectado en `requirements.txt` y `requirements.in` si existe.

---

## flake8 + isort — Calidad de código

**Job:** `backend-lint` (mismo job que bandit y pip-audit)

Aunque no son herramientas de seguridad en sentido estricto, la consistencia del código
reduce la probabilidad de introducir bugs por confusión:

- **flake8:** detecta errores de sintaxis, imports no usados, variables no definidas.
- **isort:** verifica que los imports estén ordenados. Reduce diffs innecesarios en PRs.

**Configuración en `backend/setup.cfg`:**
- `max-line-length = 120`
- Exclusiones: `migrations/`, `__pycache__/`, `.venv/`, `smoke_tests/`
- isort excluye `*/migrations/*` via `skip_glob`

---

## Por qué no hay container scan

El job de Trivy (container scan) fue removido porque el binario no podía descargarse
de forma confiable desde el entorno CI de GitHub Actions. Como alternativa:

- Las dependencias Python ya están cubiertas por `pip-audit`.
- El Dockerfile hace `apt-get upgrade -y` en build, lo que actualiza paquetes del sistema con parches disponibles.
- Si en el futuro se quiere agregar container scanning, considerar ejecutarlo localmente con `trivy image` antes de hacer push, o usar un servicio de registry con scanning integrado (Docker Hub, GitHub Container Registry, etc.).
