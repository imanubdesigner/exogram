#!/bin/bash
# Elimina todas las migraciones del backend excepto __init__.py y sus __pycache__

find backend -path "*/migrations/*.py" ! -name "__init__.py" -delete
find backend -path "*/migrations/__pycache__/*.pyc" ! -name "__init__*.pyc" -delete

echo "Migraciones eliminadas."
