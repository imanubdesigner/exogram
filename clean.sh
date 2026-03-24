#!/bin/bash

# Script de limpieza completa de Exogram
# Elimina contenedores, volúmenes, imágenes y archivos generados
# Después de ejecutar esto, puedes volver a correr ./scripts/seed_local.sh

set -e

# Colores
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

CLEAN_MIGRATIONS=false
for arg in "$@"; do
    case "$arg" in
        --with-migrations)
            CLEAN_MIGRATIONS=true
            ;;
    esac
done

COMPOSE_CMD=""
if docker compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
fi

compose_down() {
    if [ -z "$COMPOSE_CMD" ]; then
        echo "  ⚠️  docker compose/docker-compose no está disponible"
        return 0
    fi

    if ! $COMPOSE_CMD down "$@" >/dev/null 2>&1; then
        return 1
    fi
}

remove_path() {
    local path="$1"
    local label="$2"

    if [ ! -e "$path" ]; then
        echo "  No hay $label"
        return 0
    fi

    if rm -rf "$path" 2>/dev/null; then
        echo "  ✓ $label eliminado"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        if sudo rm -rf "$path" 2>/dev/null; then
            echo "  ✓ $label eliminado (con sudo)"
            return 0
        fi
    fi

    echo "  ⚠️  No se pudo eliminar $label ($path)"
    return 0
}

clean_django_migrations() {
    local local_ok=true

    find backend -path '*/migrations/*.py' ! -name '__init__.py' -delete 2>/dev/null || local_ok=false
    find backend -path '*/migrations/*.pyc' -delete 2>/dev/null || local_ok=false
    find backend -path '*/migrations/__pycache__' -exec rm -rf {} + 2>/dev/null || local_ok=false

    if [ "$local_ok" = true ]; then
        echo "  ✓ Migraciones de todas las apps limpiadas"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        if sudo find backend -path '*/migrations/*.py' ! -name '__init__.py' -delete 2>/dev/null \
            && sudo find backend -path '*/migrations/*.pyc' -delete 2>/dev/null \
            && sudo find backend -path '*/migrations/__pycache__' -exec rm -rf {} + 2>/dev/null; then
            echo "  ✓ Migraciones de todas las apps limpiadas (con sudo)"
            return 0
        fi
    fi

    echo "  ⚠️  No se pudieron limpiar todas las migraciones (revisar permisos)"
    return 0
}

clean_python_cache_in_dir() {
    local dir="$1"
    local label="$2"
    local local_ok=true

    if [ ! -d "$dir" ]; then
        echo "  No hay directorio $dir"
        return 0
    fi

    find "$dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || local_ok=false
    find "$dir" -type f -name "*.pyc" -delete 2>/dev/null || local_ok=false
    find "$dir" -type f -name "*.pyo" -delete 2>/dev/null || local_ok=false

    if [ "$local_ok" = true ]; then
        echo "  ✓ $label"
        return 0
    fi

    if command -v sudo >/dev/null 2>&1; then
        if sudo find "$dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null \
            && sudo find "$dir" -type f -name "*.pyc" -delete 2>/dev/null \
            && sudo find "$dir" -type f -name "*.pyo" -delete 2>/dev/null; then
            echo "  ✓ $label (con sudo)"
            return 0
        fi
    fi

    echo "  ⚠️  No se pudo limpiar completamente $label"
    return 0
}

echo -e "${RED}⚠️  LIMPIEZA COMPLETA DE EXOGRAM ⚠️${NC}"
echo ""
echo "Este script eliminará:"
echo "  - Todos los contenedores Docker"
echo "  - Volúmenes de PostgreSQL (¡perderás todos los datos!)"
echo "  - Imágenes construidas"
echo "  - Migraciones de Django (solo con --with-migrations, borra archivos en el repo)"
echo "  - Archivos de caché de Python"
echo "  - node_modules del frontend"
echo ""
read -p "¿Estás seguro? (escribe 'SI' para continuar): " confirmacion

if [ "$confirmacion" != "SI" ]; then
    echo -e "${GREEN}Cancelado. No se eliminó nada.${NC}"
    exit 0
fi

echo ""
echo -e "${YELLOW}Iniciando limpieza...${NC}"

# 1. Detener todos los contenedores
echo -e "${YELLOW}1. Deteniendo contenedores...${NC}"
compose_down || echo "  No hay contenedores corriendo"

# 2. Eliminar volúmenes (datos de PostgreSQL)
echo -e "${YELLOW}2. Eliminando volúmenes...${NC}"
compose_down -v || echo "  No hay volúmenes para eliminar"

# 3. Eliminar imágenes construidas
echo -e "${YELLOW}3. Eliminando imágenes Docker...${NC}"
compose_down --rmi local || echo "  No hay imágenes locales para eliminar"

# 4. Limpiar migraciones de Django (opcional)
echo -e "${YELLOW}4. Migraciones de Django...${NC}"
if [ "$CLEAN_MIGRATIONS" = true ]; then
    clean_django_migrations
else
    echo "  Saltando (usar --with-migrations para limpiar archivos de migración)"
fi

# 5. Limpiar cache de Python
echo -e "${YELLOW}5. Limpiando cache de Python...${NC}"
clean_python_cache_in_dir "backend" "Cache de Python limpiado"

# 6. Eliminar node_modules y builds del frontend
echo -e "${YELLOW}6. Limpiando artefactos del frontend...${NC}"
remove_path "frontend/node_modules/.vite" "cache de .vite"
remove_path "frontend/node_modules" "node_modules"
remove_path "frontend/dist" "dist"

# 7. Eliminar archivos de entorno copiados
echo -e "${YELLOW}7. Limpiando archivos de entorno...${NC}"
remove_path "backend/.env" ".env"

# 8. Limpiar cache de Python en exogram (sin borrar código fuente)
echo -e "${YELLOW}8. Limpiando cache dentro de backend/exogram...${NC}"
clean_python_cache_in_dir "backend/exogram" "Cache de exogram limpiado"

# 9. Limpiar modelos ONNX descargados
echo -e "${YELLOW}9. Limpiando modelos ONNX...${NC}"
remove_path "backend/onnx_models" "Modelos ONNX"
# el directorio de cache puede estar en la raíz o dentro de backend/
remove_path "backend/models_cache" "Cache de modelos (backend dir)"
remove_path "models_cache" "Cache de modelos (raíz)"

# 10. Limpiar media y static
echo -e "${YELLOW}10. Limpiando archivos media y static...${NC}"
if [ -d "backend/media" ]; then
    if find backend/media -type f -delete 2>/dev/null; then
        echo "  ✓ Media limpiado"
    elif command -v sudo >/dev/null 2>&1 && sudo find backend/media -type f -delete 2>/dev/null; then
        echo "  ✓ Media limpiado (con sudo)"
    else
        echo "  ⚠️  No se pudo limpiar completamente media"
    fi
else
    echo "  No hay directorio media"
fi

remove_path "backend/staticfiles" "Static files"

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}  ✨ Limpieza completada exitosamente ✨${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "El proyecto está limpio. Para volver a configurar y sembrar datos locales:"
echo "  ./scripts/seed_local.sh"
echo ""
