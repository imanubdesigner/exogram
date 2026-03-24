"""
Test runner personalizado para Exogram.

Extiende el runner de Django para habilitar la extensión pgvector
en la base de datos de tests antes de ejecutar migraciones/syncdb.
Sin esto, los modelos con VectorField fallan con:
  "type "vector" does not exist"
"""
import psycopg2
from django.db import connections
from django.test.runner import DiscoverRunner


class PgVectorTestRunner(DiscoverRunner):
    """
    Test runner que habilita pgvector en la test database justo después
    de crearla y antes de migrar/sincronizar apps.
    """

    def setup_databases(self, **kwargs):
        original_create_methods = {}

        # Monkey-patch _create_test_db para inyectar CREATE EXTENSION vector
        # antes de que Django corra migrate/syncdb sobre la test DB.
        for alias in connections:
            connection = connections[alias]
            if connection.vendor != 'postgresql':
                continue

            creation = connection.creation
            original = creation._create_test_db
            original_create_methods[alias] = original

            def _create_test_db_with_vector(verbosity, autoclobber, keepdb=False, *, _original=original, _connection=connection):
                result = _original(verbosity, autoclobber, keepdb)

                test_db_name = _connection.creation._get_test_db_name()
                db_params = {
                    'dbname': test_db_name,
                    'user': _connection.settings_dict.get('USER') or None,
                    'password': _connection.settings_dict.get('PASSWORD') or None,
                    'host': _connection.settings_dict.get('HOST') or None,
                    'port': _connection.settings_dict.get('PORT') or None,
                }
                db_params = {k: v for k, v in db_params.items() if v not in (None, '')}

                with psycopg2.connect(**db_params) as raw_conn:
                    with raw_conn.cursor() as cursor:
                        cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                    raw_conn.commit()

                return result

            creation._create_test_db = _create_test_db_with_vector

        try:
            return super().setup_databases(**kwargs)
        finally:
            for alias, original in original_create_methods.items():
                connections[alias].creation._create_test_db = original
