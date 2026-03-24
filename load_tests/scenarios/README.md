# Exogram Load Scenarios (Pre-Production)

> Recomendado: exportar credenciales y host antes de correr.
>
> ```bash
> export LOCUST_NICKNAME="matzalazar"
> export LOCUST_PASSWORD="admin123"
> export LOCUST_THREAD_PARTNER_NICKNAME="usuario_existente_para_chat"
> export LOCUST_HOST="http://localhost:8000"
> ```

## Scenario 1 — Baseline

- **Carga:** 10 usuarios concurrentes, ramp-up en 30 segundos.
- **Objetivo:** obtener latencias base sin contención fuerte.
- **Comando:**

```bash
locust -f load_tests/locustfile.py --headless \
  -H "$LOCUST_HOST" \
  -u 10 \
  -r 0.34 \
  -t 3m
```

- **Resultado esperado:** requests bajo SLO (discovery/affinity < 2000ms, thread polling < 500ms, highlights < 1000ms).

## Scenario 2 — Sustained Load

- **Carga:** 50 usuarios concurrentes, ramp-up en 2 minutos, ejecución total de 12 minutos.
- **Objetivo:** detectar memory leaks, agotamiento de pools (DB/Redis) y acumulación de colas Celery.
- **Comando:**

```bash
locust -f load_tests/locustfile.py --headless \
  -H "$LOCUST_HOST" \
  -u 50 \
  -r 0.42 \
  -t 12m
```

- **Monitoreo durante la corrida:**
  - **Flower:** tamaño de cola, retries, workers ocupados, latency de ejecución.
  - **PostgreSQL (`pg_stat_statements`):** queries más costosas, tiempo total por query, número de llamadas y evolución del p95 de endpoints con pgvector.

## Scenario 3 — Spike

- **Carga:** 5 usuarios por 2 minutos, salto inmediato a 100 usuarios, luego regreso a 5.
- **Objetivo:** validar comportamiento de autoscaling y recuperación sin degradación persistente tras el pico.
- **Comando para iniciar escenario interactivo (UI):**

```bash
locust -f load_tests/locustfile.py -H "$LOCUST_HOST"
```

- **Pasos en la UI de Locust:**
  - Iniciar con `Users=5`, `Spawn rate=5` y mantener 2 minutos.
  - Subir inmediatamente a `Users=100`, `Spawn rate=500` y mantener 2 minutos.
  - Bajar inmediatamente a `Users=5`, `Spawn rate=500` y mantener 2 minutos.

- **Resultado esperado:** sube error-rate durante el spike de forma acotada, y al volver a 5 usuarios la latencia/error-rate retorna al baseline sin cola residual.
