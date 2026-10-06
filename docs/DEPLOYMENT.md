# Deployment and recovery

All paths and domains below are placeholders. This repository includes no private infrastructure configuration, SSH key or site data. Choose Python 3.12 and Node.js 22.12+ for a native installation, or Docker with Compose v2. Store persistent state separately from code and keep your secrets out of Git.

## Docker

Copy `.env.example` to `.env`. Generate a secret with:

```sh
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

Set the generated value as `DJANGO_SECRET_KEY` in `.env`, then:

```sh
docker compose up -d --build
docker compose exec app python manage.py create_admins administrator
```

The container migrates the schema without loading a corpus or creating an account. Its named volume holds `/state/db.sqlite3` and `/state/media`. Open <http://localhost:8000> for local use. Published ports bind to loopback. The container runs as a non-root user. Do not run multiple application replicas against one SQLite volume.

For internet deployment, install Nginx and a valid TLS certificate on the host and adapt [nginx.conf.example](../deploy/nginx.conf.example). Set:

```dotenv
DJANGO_ALLOWED_HOSTS=corpus.example.org,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://corpus.example.org
DJANGO_SECURE_COOKIES=1
DJANGO_BEHIND_HTTPS_PROXY=1
DJANGO_SSL_REDIRECT=0
DJANGO_HSTS_SECONDS=31536000
```

Nginx redirects external HTTP to HTTPS; the app remains reachable on loopback for its health check. Validate `nginx -t`, reload it, then `docker compose up -d` to apply environment changes. Nginx must pass the original Host and overwrite `X-Forwarded-Proto`. Waitress trusts that header only from its immediate loopback proxy; restrict app network access so untrusted clients cannot supply it. If the proxy runs in a separate container, adapt trusted proxy configuration explicitly instead of trusting all proxies. The supplied configuration assumes a host Nginx.

The supplied Nginx example limits login requests to reduce password guessing. Use unique passwords, key-only SSH, a firewall allowing the needed SSH/HTTP/HTTPS ports, and regular OS/package updates. Restrict access to `.env`, database files, media and backups. Enable TLS at the proxy before enabling secure cookies; the local HTTP setup deliberately leaves secure-cookie flags off.

## Native installation

Build the frontend with `npm ci` and `npm run build`. Install backend production requirements in a virtual environment, run `manage.py migrate`, `manage.py collectstatic --noinput`, and create your administrator. Copy `backend/.env.example` to `backend/.env` and set:

```dotenv
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=YOUR_FRESH_GENERATED_SECRET
DJANGO_DB_PATH=/srv/corpus-state/db.sqlite3
DJANGO_MEDIA_ROOT=/srv/corpus-state/media
DJANGO_ALLOWED_HOSTS=corpus.example.org,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=https://corpus.example.org
DJANGO_SECURE_COOKIES=1
DJANGO_BEHIND_HTTPS_PROXY=1
DJANGO_HSTS_SECONDS=31536000
```

Create the state directory for the unprivileged service account. Run `python serve.py --host 127.0.0.1 --port 8000` under a service manager and use the same host Nginx/TLS configuration. Do not expose Django's development server. Run `python manage.py check --deploy` using production settings and review any remaining diagnostics for your environment. API docs are available at `/api/docs`; restrict them at the proxy if required by your deployment.

## Backups

Record the deployed Git commit and keep an encrypted or access-restricted copy of `.env` separately. Back up the SQLite database and uploaded media together during a brief maintenance window; this gives them a consistent point in time. Do not copy only a live `.sqlite3` file while WAL writes are active.

For Docker, prepare an empty local `backups/YYYY-MM-DD` directory with restricted permissions. During maintenance:

```sh
docker compose exec app python -c "import sqlite3; a=sqlite3.connect('/state/db.sqlite3'); b=sqlite3.connect('/state/backup.sqlite3'); a.backup(b); b.close(); a.close()"
docker compose cp app:/state/backup.sqlite3 backups/YYYY-MM-DD/db.sqlite3
docker compose cp app:/state/media backups/YYYY-MM-DD/media
docker compose exec app python -c "from pathlib import Path; Path('/state/backup.sqlite3').unlink()"
```

Stop external writes for both copies, verify the copied database with `PRAGMA integrity_check`, compute checksums and store a second copy off-server. Backups contain private corpus data and user/password-hash records; never commit them. Native installations can use the same `sqlite3.Connection.backup()` API with their own paths. Test restoration periodically.

## Rollback and rebuild

For a code-only rollback, check out the recorded previous commit and rebuild, provided its schema is compatible. Before every migration, retain a corresponding database/media backup. If a schema migration changed compatibility, stop the application, restore the matching database and media, and run the matching code version. Do not run an older application against an unknown newer schema.

After rebuilding an OS, install Docker or the native runtime on a trusted system, clone the recorded code version, create a fresh secret and administrator credentials as needed, restore the database/media into persistent state, set file ownership for the service user, then start the app. Verify login, metadata, reading, search and exports. Run `manage.py rebuild_index` if the index is missing or tokenization changed. An empty reinstallation works without a backup; restoring your corpus requires your own backup.

An OS snapshot can speed recovery, but it may also contain compromised files. After a security incident, rebuild from trusted software, rotate exposed credentials and inspect data backups before restoring. This source repository is a reproducible software baseline, not a snapshot of any existing server.

## Branding and data policies

Set `VITE_SITE_NAME` and `VITE_SITE_SUBTITLE` before rebuilding the frontend; Compose passes them as build arguments. Adapt `frontend/src/views/CitationView.vue` to describe your own dataset's rights and references. A MIT software license does not grant rights to imported corpus material.
