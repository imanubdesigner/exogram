"""
Exogram load test suite (Locust).

ANN benchmark note:
- Antes del índice HNSW en pgvector, `/api/discovery/feed/` degradaba su P95
  casi linealmente con el tamaño de tabla por nearest-neighbor exacto.
- Con ANN (HNSW), la latencia debería mantenerse aproximadamente estable
  aunque crezca el volumen de highlights/centroides.
- Este archivo es el benchmark operativo para validar esa hipótesis.
"""
import logging
import os
from typing import Optional

from locust import HttpUser, between, task
from locust.exception import StopUser


logger = logging.getLogger(__name__)

# P95 SLO targets por endpoint (ms). Si se exceden, se marca failure aunque sea HTTP 200.
DISCOVERY_SLO_MS = 2000
AFFINITY_SLO_MS = 2000
THREAD_POLL_SLO_MS = 500
HIGHLIGHTS_SLO_MS = 1000


class ExogramUser(HttpUser):
    wait_time = between(2, 8)

    def on_start(self):
        self.thread_id: Optional[int] = None
        self.nickname = os.getenv("LOCUST_NICKNAME", "matzalazar")
        self.password = os.getenv("LOCUST_PASSWORD", "admin123")
        self.thread_partner = os.getenv("LOCUST_THREAD_PARTNER_NICKNAME", "")
        self.setUp()

    def setUp(self):
        """
        Login inicial por sesión virtual.

        Locust HttpUser persiste cookies automáticamente dentro de la sesión
        del usuario virtual, replicando el comportamiento real del navegador.
        """
        payload = {"nickname": self.nickname, "password": self.password}

        # Se intenta primero la ruta pedida en el requerimiento.
        login_paths = ["/api/accounts/login/", "/api/auth/login/"]
        login_resp = None
        for path in login_paths:
            resp = self.client.post(path, json=payload, name="POST /api/accounts/login/ (or compat)")
            if resp.status_code != 404:
                login_resp = resp
                break

        if login_resp is None:
            raise StopUser("No login endpoint available (/api/accounts/login/ or /api/auth/login/).")

        try:
            login_resp.raise_for_status()
        except Exception as exc:  # pragma: no cover - locust runtime path
            raise StopUser(f"Login failed: {exc}") from exc

        if not self.client.cookies:
            raise StopUser("Login succeeded but no auth cookie was set.")

        self._ensure_thread_id()

    def _mark_slo_failure(self, name: str, response_time_ms: float, threshold_ms: int):
        logger.warning(
            "[SLO breach] %s: %.1fms > %dms",
            name,
            response_time_ms,
            threshold_ms,
        )

    def _get_with_slo(self, path: str, name: str, threshold_ms: int):
        with self.client.get(path, name=name, catch_response=True) as response:
            try:
                response.raise_for_status()
            except Exception as exc:
                response.failure(f"HTTP failure: {exc}")
                return

            response_time_ms = response.elapsed.total_seconds() * 1000
            # SLO operacional: aunque status sea 200, si supera umbral cuenta como falla.
            if response_time_ms > threshold_ms:
                self._mark_slo_failure(name, response_time_ms, threshold_ms)
                response.failure(f"SLO breach: {response_time_ms:.1f}ms > {threshold_ms}ms")

    def _ensure_thread_id(self):
        if self.thread_id:
            return

        resp = self.client.get("/api/threads/", name="GET /api/threads/ (bootstrap)")
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            if results:
                self.thread_id = results[0].get("id")
                return

        if not self.thread_partner:
            return

        create = self.client.post(
            "/api/threads/",
            json={
                "other_nickname": self.thread_partner,
                "context_book_title": "Locust Load Test",
            },
            name="POST /api/threads/ (bootstrap)",
        )
        if create.status_code in (200, 201):
            self.thread_id = create.json().get("id")

    @task(3)
    def discovery_feed(self):
        self._get_with_slo(
            "/api/discovery/feed/?limit=20",
            "GET /api/discovery/feed/",
            DISCOVERY_SLO_MS,
        )

    @task(2)
    def similar_readers(self):
        self._get_with_slo(
            "/api/affinity/similar-readers/?limit=10",
            "GET /api/affinity/similar-readers/",
            AFFINITY_SLO_MS,
        )

    @task(5)
    def thread_polling(self):
        if not self.thread_id:
            self._ensure_thread_id()
        if not self.thread_id:
            logger.warning(
                "Thread polling skipped: no thread available. "
                "Set LOCUST_THREAD_PARTNER_NICKNAME or seed threads."
            )
            return

        self._get_with_slo(
            f"/api/threads/{self.thread_id}/",
            "GET /api/threads/{id}/",
            THREAD_POLL_SLO_MS,
        )

    @task(2)
    def highlights_list(self):
        self._get_with_slo(
            "/api/highlights/?page=1",
            "GET /api/highlights/",
            HIGHLIGHTS_SLO_MS,
        )
