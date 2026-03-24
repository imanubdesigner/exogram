#!/usr/bin/env bash
# Seed a fully usable local Exogram environment for manual UI testing.
# This script consolidates infrastructure bootstrap + data seeding in one place:
# it brings up services, applies DB prerequisites/migrations, and then creates
# a fake social graph plus highlight data for affinity/discovery/social testing.
# Local-only: never run against production databases or production settings.
# It depends on Docker Compose and expects at least one My Clippings `.txt`
# file in `clippings_examples/` for meaningful highlight seeding.
#
# Setup scope: this script handles full local stack setup and data seeding.
# You can run it on a fresh DB (initial bootstrap + first seed) or re-run it
# on an existing DB (idempotent updates, duplicate-safe imports where possible).

set -euo pipefail
# -e: abort immediately if any command fails
# -u: fail on unset variables (avoids silent mistakes)
# -o pipefail: fail pipelines if any command in the chain fails

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

# Guardrail: this script creates disposable local data.
# It is intentionally blocked unless settings module is unset or clearly local/ci.
if [[ -n "${DJANGO_SETTINGS_MODULE:-}" ]]; then
  MODULE_LC="$(printf '%s' "${DJANGO_SETTINGS_MODULE}" | tr '[:upper:]' '[:lower:]')"
  if [[ "${DJANGO_SETTINGS_MODULE}" == "exogram.settings" ]]; then
    echo "ERROR: DJANGO_SETTINGS_MODULE=exogram.settings is not allowed for seed_local.sh." >&2
    echo "This script is local-only and must never run against production-like settings." >&2
    exit 1
  fi
  if [[ "${MODULE_LC}" != *local* && "${MODULE_LC}" != *ci* ]]; then
    echo "ERROR: DJANGO_SETTINGS_MODULE must contain 'local' or 'ci' (or be unset)." >&2
    echo "Current value: ${DJANGO_SETTINGS_MODULE}" >&2
    exit 1
  fi
fi

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
else
  echo "ERROR: docker compose (or docker-compose) not found." >&2
  exit 1
fi

run_shell() {
  local script="$1"
  shift || true
  if [[ "$#" -gt 0 ]]; then
    "${COMPOSE[@]}" exec -T backend env "$@" python manage.py shell -c "${script}"
  else
    "${COMPOSE[@]}" exec -T backend python manage.py shell -c "${script}"
  fi
}

generate_password() {
  "${COMPOSE[@]}" exec -T backend python -c "import secrets; print(secrets.token_urlsafe(18))" | tr -d '\r\n'
}

dir_has_files() {
  local dir="$1"
  [[ -d "$dir" ]] && [[ -n "$(find "$dir" -type f 2>/dev/null | head -1)" ]]
}

echo "==> Step 0: Ensuring local env file exists..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ ! -f "backend/.env" ]]; then
  cp .env.example backend/.env
  echo "Created backend/.env from .env.example"
else
  echo "backend/.env already exists"
fi

echo "==> Step 1: Verifying backend directory permissions..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ -d "backend/exogram" && ! -w "backend/exogram" ]]; then
  echo "backend/exogram is not writable; trying to fix ownership..."
  if command -v sudo >/dev/null 2>&1; then
    sudo chown -R "$(whoami)":"$(whoami)" backend/exogram/ || {
      echo "WARNING: could not update backend/exogram permissions automatically." >&2
    }
  else
    echo "WARNING: sudo is unavailable, cannot auto-fix backend/exogram permissions." >&2
  fi
else
  echo "Permissions look OK."
fi

echo "==> Step 1.1: Ensuring backend startup script is executable..."
# Docker bind mounts preserve host mode bits. If start-web.sh is not +x on host,
# container startup fails with `exec: \"./start-web.sh\": permission denied`.
if [[ ! -f "backend/start-web.sh" ]]; then
  echo "ERROR: backend/start-web.sh not found." >&2
  exit 1
fi
if [[ ! -x "backend/start-web.sh" ]]; then
  chmod +x backend/start-web.sh
  echo "Applied +x to backend/start-web.sh"
else
  echo "backend/start-web.sh already executable."
fi

echo "==> Step 2: Starting core infrastructure services..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
"${COMPOSE[@]}" up -d db redis

echo "==> Step 3: Waiting for PostgreSQL readiness..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
until "${COMPOSE[@]}" exec -T db pg_isready -U exogram >/dev/null 2>&1; do
  sleep 2
done

echo "==> Step 4: Enabling pgvector extension..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
until "${COMPOSE[@]}" exec -T db psql -U exogram -d exogram \
  -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null 2>&1; do
  sleep 2
done

echo "==> Step 5: Building backend image (can be skipped)..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ "${SEED_SKIP_BACKEND_BUILD:-0}" == "1" ]]; then
  echo "Skipped backend build (SEED_SKIP_BACKEND_BUILD=1)."
else
  "${COMPOSE[@]}" build --no-cache backend
fi

echo "==> Step 6: Running migrations checks and apply..."
# Genera migraciones pendientes si existen (después de cambios a models.py):
"${COMPOSE[@]}" run --rm backend python manage.py makemigrations
"${COMPOSE[@]}" run --rm backend python manage.py migrate --noinput --fake-initial

echo "==> Step 7: Installing frontend dependencies (can be skipped)..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ "${SEED_SKIP_FRONTEND_NPM_INSTALL:-0}" == "1" ]]; then
  echo "Skipped frontend npm install (SEED_SKIP_FRONTEND_NPM_INSTALL=1)."
else
  "${COMPOSE[@]}" run --rm frontend npm install
fi

echo "==> Step 8: Preparing ONNX model cache (can be skipped)..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ "${SEED_SKIP_MODEL_DOWNLOAD:-0}" == "1" ]]; then
  echo "Skipped model download (SEED_SKIP_MODEL_DOWNLOAD=1)."
else
  ROOT_CACHE_DIR="./models_cache"
  LEGACY_CACHE_DIR="./backend/models_cache"
  MODEL_FILE="${ROOT_CACHE_DIR}/paraphrase-multilingual-MiniLM-L12-v2.onnx"
  TOKENIZER_FILE="${ROOT_CACHE_DIR}/tokenizer.json"
  MIN_MODEL_SIZE=$((400 * 1024 * 1024))

  if ! dir_has_files "${ROOT_CACHE_DIR}" && dir_has_files "${LEGACY_CACHE_DIR}"; then
    mkdir -p "${ROOT_CACHE_DIR}"
    cp -a "${LEGACY_CACHE_DIR}/." "${ROOT_CACHE_DIR}/" || true
  fi

  CACHE_INVALID_REASONS=""
  if [[ ! -f "${MODEL_FILE}" ]]; then
    CACHE_INVALID_REASONS="missing model.onnx"
  else
    MODEL_SIZE=$(stat -c%s "${MODEL_FILE}" 2>/dev/null || echo 0)
    if [[ "${MODEL_SIZE}" -lt "${MIN_MODEL_SIZE}" ]]; then
      CACHE_INVALID_REASONS="incomplete model.onnx"
    fi
  fi

  if [[ ! -f "${TOKENIZER_FILE}" ]]; then
    if [[ -n "${CACHE_INVALID_REASONS}" ]]; then
      CACHE_INVALID_REASONS="${CACHE_INVALID_REASONS}; missing tokenizer.json"
    else
      CACHE_INVALID_REASONS="missing tokenizer.json"
    fi
  fi

  if [[ -n "${CACHE_INVALID_REASONS}" ]]; then
    echo "Model cache invalid: ${CACHE_INVALID_REASONS}"
    "${COMPOSE[@]}" run --rm backend python manage.py download_onnx_model --cache-dir ./models_cache || true
  else
    echo "Model cache already available."
  fi
fi

echo "==> Step 9: Starting application services..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
"${COMPOSE[@]}" up -d backend celery celery-beat frontend
if "${COMPOSE[@]}" config --services | grep -q '^flower$'; then
  "${COMPOSE[@]}" up -d flower
fi

echo "==> Step 10: Backend health check..."
if ! "${COMPOSE[@]}" ps --services --status running | grep -q "^backend$"; then
  echo "ERROR: backend service is not running." >&2
  echo "Run: docker compose up -d" >&2
  exit 1
fi
if ! "${COMPOSE[@]}" exec -T backend python manage.py check >/dev/null 2>&1; then
  echo "ERROR: backend health check failed." >&2
  echo "Ensure the stack is up and healthy first: docker compose up -d" >&2
  exit 1
fi
echo "OK: backend service is running and Django checks pass."

FRONTEND_LOGIN_URL="${FRONTEND_LOGIN_URL:-http://localhost:5173/login}"
BACKEND_CONTAINER_ID="$("${COMPOSE[@]}" ps -q backend)"
if [[ -z "${BACKEND_CONTAINER_ID}" ]]; then
  echo "ERROR: could not resolve backend container id." >&2
  exit 1
fi

GENESIS_USERNAME="genesis_reader"
GENESIS_EMAIL="genesis@local.test"
COHORT_USERS=(
  "reader_philosophy"
  "reader_fiction"
  "reader_science"
  "reader_history"
  "reader_poetry"
)

echo "==> Step 11: Creating genesis user..."
GENESIS_EXISTS="$(run_shell "from django.contrib.auth.models import User; print('1' if User.objects.filter(username='${GENESIS_USERNAME}').exists() else '0')" | tr -d '\r\n')"
GENESIS_PASSWORD_DISPLAY="<existing user; password unchanged>"
if [[ "${GENESIS_EXISTS}" == "1" ]]; then
  echo "Notice: ${GENESIS_USERNAME} already exists. Skipping creation."
else
  GENESIS_PASSWORD="$(generate_password)"
  # Printing local test credentials to stdout is intentional here for developer convenience.
  # This would be unacceptable in production workflows.
  run_shell "$(cat <<'PY'
import os
from django.contrib.auth.models import User

username = os.environ["GENESIS_USERNAME"]
email = os.environ["GENESIS_EMAIL"]
password = os.environ["GENESIS_PASSWORD"]

user = User.objects.create_user(username=username, email=email, password=password)
profile = user.profile
profile.nickname = username
profile.verified_email = email
profile.invited_by = None
profile.onboarding_completed = True
profile.comment_allowance_depth = 5
profile.invitation_depth = 0
profile.save()
print("created")
PY
)" \
    GENESIS_USERNAME="${GENESIS_USERNAME}" \
    GENESIS_EMAIL="${GENESIS_EMAIL}" \
    GENESIS_PASSWORD="${GENESIS_PASSWORD}" >/dev/null
  GENESIS_PASSWORD_DISPLAY="${GENESIS_PASSWORD}"
  echo "Genesis user created. Password: ${GENESIS_PASSWORD}"
fi

echo "==> Step 12: Creating/updating cohort users..."
COHORT_PASSWORD="$(generate_password)"
echo "Test cohort password: ${COHORT_PASSWORD}"

# Graph structure matters: invitation-distance, trust behavior, and social permissions
# depend on users being connected under the same invitation tree root.
run_shell "$(cat <<'PY'
import os
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import Invitation

cohort_users = [
    "reader_philosophy",
    "reader_fiction",
    "reader_science",
    "reader_history",
    "reader_poetry",
]

genesis = User.objects.get(username="genesis_reader")
password = os.environ["COHORT_PASSWORD"]

for username in cohort_users:
    email = f"{username}@local.test"
    user, created = User.objects.get_or_create(username=username, defaults={"email": email})
    user.email = email
    user.set_password(password)
    user.save()

    profile = user.profile
    profile.nickname = username
    profile.verified_email = email
    profile.invited_by = genesis
    profile.onboarding_completed = True
    profile.invitation_depth = 1
    profile.save()

    invitation, _ = Invitation.objects.get_or_create(
        email=email,
        defaults={
            "invited_by": genesis,
            "expires_at": timezone.now() + timedelta(days=3650),
        },
    )
    invitation.invited_by = genesis
    invitation.is_used = True
    invitation.used_at = invitation.used_at or timezone.now()
    if invitation.expires_at is None or invitation.expires_at <= timezone.now():
        invitation.expires_at = timezone.now() + timedelta(days=3650)
    if invitation.created_user_id in (None, user.id):
        invitation.created_user = user
    invitation.save()

    if profile.invitation_used_id != invitation.id:
        profile.invitation_used = invitation
        profile.save(update_fields=["invitation_used", "updated_at"])

    print(f"{username}:{'created' if created else 'existing'}")
PY
)" \
  COHORT_PASSWORD="${COHORT_PASSWORD}"

echo "==> Step 13: Extending invitation tree with random descendants..."
RANDOM_DESC_TARGET="${RANDOM_DESC_TARGET:-5}"
run_shell "$(cat <<'PY'
import os
import secrets
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.models import User
from accounts.models import Invitation

password = os.environ["COHORT_PASSWORD"]
target = int(os.environ["RANDOM_DESC_TARGET"])
parents = [
    User.objects.get(username="reader_philosophy"),
    User.objects.get(username="reader_fiction"),
    User.objects.get(username="reader_science"),
    User.objects.get(username="reader_history"),
    User.objects.get(username="reader_poetry"),
]

existing = list(User.objects.filter(username__startswith="reader_random_").order_by("username"))
for u in existing:
    u.set_password(password)
    u.save(update_fields=["password"])

while len(existing) < target:
    suffix = secrets.token_hex(2)
    username = f"reader_random_{suffix}"
    if User.objects.filter(username=username).exists():
        continue

    email = f"{username}@local.test"
    parent = parents[len(existing) % len(parents)]
    user = User.objects.create_user(username=username, email=email, password=password)

    profile = user.profile
    profile.nickname = username
    profile.verified_email = email
    profile.invited_by = parent
    profile.onboarding_completed = True
    profile.invitation_depth = parent.profile.invitation_depth + 1
    profile.save()

    invitation = Invitation.objects.create(
        email=email,
        invited_by=parent,
        expires_at=timezone.now() + timedelta(days=3650),
        is_used=True,
        used_at=timezone.now(),
        created_user=user,
    )
    profile.invitation_used = invitation
    profile.save(update_fields=["invitation_used", "updated_at"])

    existing.append(user)
    print(f"{username}:created parent={parent.username}")

print(f"random_descendants_total={len(existing)}")
PY
)" \
  COHORT_PASSWORD="${COHORT_PASSWORD}" \
  RANDOM_DESC_TARGET="${RANDOM_DESC_TARGET}"

echo "==> Step 14: Importing clippings_examples/*.txt through API endpoints..."
CLIPPINGS_DIR="${ROOT_DIR}/clippings_examples"
if [[ ! -d "${CLIPPINGS_DIR}" ]]; then
  echo "ERROR: ${CLIPPINGS_DIR} does not exist." >&2
  echo "Add at least one My Clippings .txt file to seed highlight data." >&2
  exit 1
fi

mapfile -t CLIPPINGS_FILES < <(find "${CLIPPINGS_DIR}" -maxdepth 1 -type f -name '*.txt' | sort)
if [[ "${#CLIPPINGS_FILES[@]}" -eq 0 ]]; then
  echo "ERROR: no .txt files found in ${CLIPPINGS_DIR}." >&2
  echo "Add at least one My Clippings .txt file to seed highlight data." >&2
  exit 1
fi

# This import path intentionally goes through upload/import endpoints so parsing,
# deduplication, and async embedding enqueueing all execute as in real usage.
# Without this step, affinity/discovery often stays empty or returns not_ready.
# For this short-lived shell process we use an in-memory Celery result backend to
# avoid noisy AsyncResult cleanup tracebacks tied to Redis result backend teardown.
"${COMPOSE[@]}" exec -T backend mkdir -p /tmp/seed_clippings

ALL_TARGET_USERS=("${COHORT_USERS[@]}")
while IFS= read -r random_user; do
  [[ -n "${random_user}" ]] && ALL_TARGET_USERS+=("${random_user}")
done < <(run_shell "from django.contrib.auth.models import User; [print(u.username) for u in User.objects.filter(username__startswith='reader_random_').order_by('username')]")

for idx in "${!CLIPPINGS_FILES[@]}"; do
  src_file="${CLIPPINGS_FILES[$idx]}"
  target_user="${ALL_TARGET_USERS[$((idx % ${#ALL_TARGET_USERS[@]}))]}"
  container_file="/tmp/seed_clippings/$(basename "${src_file}")"

  echo "  -> $(basename "${src_file}") assigned to ${target_user}"
  docker cp "${src_file}" "${BACKEND_CONTAINER_ID}:${container_file}"

  run_shell "$(cat <<'PY'
import os
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

username = os.environ["SEED_USERNAME"]
password = os.environ["SEED_PASSWORD"]
filepath = os.environ["SEED_FILEPATH"]
seed_http_host = os.environ.get("SEED_HTTP_HOST", "localhost")

client = APIClient(enforce_csrf_checks=True)
client.defaults["HTTP_HOST"] = seed_http_host
login = client.post(
    "/api/auth/login/",
    {"nickname": username, "password": password},
    format="json",
    HTTP_HOST=seed_http_host,
)
if login.status_code != 200:
    raise SystemExit(f"login_failed:{login.status_code}")

csrf_cookie = login.cookies.get(settings.CSRF_COOKIE_NAME)
if csrf_cookie is None:
    raise SystemExit("csrf_cookie_missing")
client.credentials(HTTP_X_CSRFTOKEN=csrf_cookie.value)

with open(filepath, "rb") as f:
    uploaded = SimpleUploadedFile(os.path.basename(filepath), f.read(), content_type="text/plain")
upload = client.post(
    "/api/highlights/upload/",
    {"file": uploaded},
    format="multipart",
    HTTP_HOST=seed_http_host,
)
if upload.status_code != 200:
    raise SystemExit(f"upload_failed:{upload.status_code}")

highlights = upload.data.get("highlights", [])
if not highlights:
    print("no_highlights_parsed")
    raise SystemExit(0)

result = client.post(
    "/api/highlights/import/",
    {"highlights": highlights},
    format="json",
    HTTP_HOST=seed_http_host,
)
if result.status_code != 201:
    raise SystemExit(f"import_failed:{result.status_code}")

print(
    f"imported={result.data.get('imported', 0)} "
    f"skipped_duplicates={result.data.get('skipped_duplicates', 0)}"
)
PY
)" \
    CELERY_RESULT_BACKEND="cache+memory://" \
    SEED_USERNAME="${target_user}" \
    SEED_PASSWORD="${COHORT_PASSWORD}" \
    SEED_FILEPATH="${container_file}" \
    SEED_HTTP_HOST="${SEED_HTTP_HOST:-localhost}"
done

echo "==> Step 15: Filling missing embeddings (can be skipped)..."
# Consolidated from setup.sh during 2026-03-08 cleanup.
if [[ "${SEED_SKIP_FILL_EMBEDDINGS:-0}" == "1" ]]; then
  echo "Skipped fill_embeddings (SEED_SKIP_FILL_EMBEDDINGS=1)."
else
  # fill_embeddings triggers Highlight post_save hooks, which enqueue Celery tasks.
  # Use an in-memory result backend for this short-lived process to avoid noisy
  # AsyncResult cleanup tracebacks from Redis result backend teardown.
  "${COMPOSE[@]}" run --rm backend env CELERY_RESULT_BACKEND=cache+memory:// python manage.py fill_embeddings --batch-size 32 || true
fi

echo
ALL_USERS=("${GENESIS_USERNAME}" "${COHORT_USERS[@]}")
while IFS= read -r random_user; do
  [[ -n "${random_user}" ]] && ALL_USERS+=("${random_user}")
done < <(run_shell "from django.contrib.auth.models import User; [print(u.username) for u in User.objects.filter(username__startswith='reader_random_').order_by('username')]")

echo "+----------------------+----------------------------------+"
echo "| Username             | Login URL                        |"
echo "+----------------------+----------------------------------+"
for username in "${ALL_USERS[@]}"; do
  printf "| %-20s | %-32s |\n" "${username}" "${FRONTEND_LOGIN_URL}"
done
echo "+----------------------+----------------------------------+"
echo "Genesis password: ${GENESIS_PASSWORD_DISPLAY}"
echo "Shared cohort password: ${COHORT_PASSWORD}"
echo "Reminder: all records were created in the local development database only."
