#!/usr/bin/env sh
set -e

echo "🔧 Entry: $@"

# --- Wait for Postgres (only if POSTGRES_HOST is set) ---
if [ -n "$POSTGRES_HOST" ]; then
  echo "⏳ Waiting for Postgres at $POSTGRES_HOST:${POSTGRES_PORT:-5432}..."
  ATTEMPTS=0
  until python - <<'PY'
import os, sys, socket
host=os.getenv("POSTGRES_HOST","localhost")
port=int(os.getenv("POSTGRES_PORT","5432"))
s=socket.socket()
s.settimeout(1.5)
try:
    s.connect((host, port))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
PY
  do
    ATTEMPTS=$((ATTEMPTS+1))
    if [ "$ATTEMPTS" -ge 60 ]; then
      echo "⚠️  Postgres not ready after 60s, continuing anyway..."
      break
    fi
    echo "… still waiting ($ATTEMPTS/60)"
    sleep 1
  done
fi

# --- Django migrations (optional) ---
if [ "${DJANGO_MIGRATE:-1}" = "1" ]; then
  echo "🚀 Applying migrations..."
  python manage.py migrate --noinput
fi

# --- Optional superuser (non-interactive) ---
if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL:-}" ]; then
  echo "👑 Ensuring admin user exists..."
  python manage.py createsuperuser --noinput || true
fi

# --- Optional seed step (runs only if file exists) ---
if [ "${DB_SEED:-0}" = "1" ]; then
  if [ -f "seed_db.py" ]; then
    echo "🌱 Seeding database..."
    python manage.py shell < seed_db.py
  else
    echo "⚠️  DB_SEED=1 but seed_db.py not found; skipping."
  fi
fi

# --- Optional collectstatic ---
if [ "${COLLECTSTATIC:-0}" = "1" ]; then
  echo "🧹 Collecting static files..."
  python manage.py collectstatic --noinput
fi

# --- Optional: add django-crontab entries ---
if [ "${DJANGO_CRONTAB_ADD:-0}" = "1" ]; then
  echo "🕒 Adding django-crontab entries..."
  python manage.py crontab add || true
fi

echo "✅ Ready. Executing: $@"
exec "$@"
