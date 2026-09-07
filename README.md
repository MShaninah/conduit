# Conduit Container

A fully containerized deployment of [Conduit](https://realworld-docs.netlify.app/) — the
"RealWorld" Medium.com-style blogging platform — built as a Docker
containerization exercise for Developer Akademie. It packages the official
[`conduit-backend`](https://github.com/Developer-Akademie-DevSecOpsKurs/conduit-backend)
(Django REST Framework) and
[`conduit-frontend`](https://github.com/Developer-Akademie-DevSecOpsKurs/conduit-frontend)
(Angular) reference apps, kept on their original pinned dependencies and
containerized around them.

## Table of Contents

- [Quickstart](#quickstart)
- [Description](#description)
- [Usage](#usage)
  - [Repository structure](#repository-structure)
  - [Environment variables](#environment-variables)
  - [Docker images](#docker-images)
  - [docker-compose services](#docker-compose-services)
  - [Changing the backend](#changing-the-backend)
  - [Changing the frontend](#changing-the-frontend)
  - [Database and data persistence](#database-and-data-persistence)
  - [Viewing and persisting logs](#viewing-and-persisting-logs)
- [Security notes](#security-notes)

## Quickstart

**Prerequisites:**

- Docker Engine with the Compose plugin (`docker compose version` should work)

**Steps:**

1. Copy the environment template and fill in real secrets:
   ```bash
   cp .env.example .env
   ```
   At minimum, set `POSTGRES_PASSWORD` and `SECRET_KEY` in `.env` to your own
   values (see [Environment variables](#environment-variables)).

2. Build and start all services:
   ```bash
   docker compose up -d --build
   ```

3. Open the app: **http://localhost:8282** (or `http://<your-server-ip>:8282`
   on a remote host/VM).

4. Stop everything:
   ```bash
   docker compose down
   ```
   (add `-v` to also delete the database volume and wipe all data)


## Description

This repository contains a complete, self-hosted Conduit application split into
three containers orchestrated with Docker Compose:

- **`frontend`** — the official Angular SPA, implementing the full Conduit
  UI: registration/login, global/personal article feeds, tag filtering,
  article CRUD, favoriting, comments, following, and user profiles/settings.
  Served in production by Nginx, which also reverse-proxies `/api/*`
  requests to the backend so the browser only ever talks to one origin.
- **`backend`** — the official Django REST Framework app implementing the
  [RealWorld API spec](https://realworld-docs.netlify.app/specifications/backend/endpoints/)
  (JWT auth, users, profiles, articles, comments, tags), served in production
  by Gunicorn (a WSGI server — never Django's built-in `runserver`).
- **`database`** — PostgreSQL, with its data directory persisted in a named
  Docker volume.

The upstream repos are from 2016 (Django 1.10, DRF 3.4, PyJWT 1.4) and no
longer install against a current Python. Part of the point of this exercise is
learning to deal with deprecated dependencies rather than upgrading past them,
so `backend/requirements.txt` keeps the original pins untouched and the
container is built to suit them: the backend image is based on
`python:3.5-slim`, the newest interpreter Django 1.10 supports. Only two
dependencies are added — `psycopg2-binary` and `gunicorn` — because running
against Postgres behind a real WSGI server is a containerization requirement,
not an upstream one; both are pinned to their last Python 3.5-compatible
releases.

Because Debian buster (the base of `python:3.5-slim`) is end-of-life, its
packages are pulled from `archive.debian.org` — see the comment in
`backend/Dockerfile`. Treat this image as a teaching artifact: it is built
from an unsupported interpreter and an unsupported base OS, and it is not
something to expose to real traffic.

The Angular frontend's dependencies were already current and needed no version
bump, only pointing it at this repo's own backend instead of the public
`api.realworld.io` demo API. See
`archive/from-scratch-flask-vue/` for an earlier, from-scratch
reimplementation of the same spec that predates switching to these upstream
repos; it is kept for reference only and is not part of the running stack.

The purpose of this repository is not to demonstrate novel product features,
but to show a correct, secure, production-shaped containerization of a
full-stack app: multi-stage Dockerfiles, environment-based configuration,
crash-resilient services, and a documented developer workflow.

## Usage

### Repository structure

```
.
├── backend/                  Django REST Framework API (RealWorld backend)
│   ├── conduit/               Project package (settings, urls, wsgi, apps/)
│   │   └── apps/               authentication, profiles, articles, core
│   ├── manage.py
│   ├── Dockerfile              Multi-stage build → Gunicorn WSGI image
│   ├── entrypoint.sh            Waits for Postgres, runs migrations, starts Gunicorn
│   └── requirements.txt
├── frontend/                  Angular SPA (RealWorld frontend)
│   ├── src/app/                 Core services/interceptors, feature modules
│   ├── nginx/                    Nginx config template (Nginx image, not a dev server)
│   └── Dockerfile                Multi-stage build → static bundle served by Nginx
├── archive/from-scratch-flask-vue/  Superseded Flask+Vue reimplementation (reference only)
├── docker-compose.yaml        Orchestrates frontend + backend + database
├── .env.example                Template for required environment variables
└── README.md
```

Each service directory has its own `.dockerignore`, since each is built with
its own Docker build context (`./backend` and `./frontend` respectively).

### Environment variables

All variables use `UPPER_CASE_WITH_UNDERSCORE` and are referenced with
`${...}` brace notation throughout the Dockerfiles and `docker-compose.yaml`.

Critical values (credentials/secrets) are **never** hardcoded or committed.
They live only in your local `.env` file (gitignored). The `database` and
`backend` services load it wholesale with `env_file: .env`; the `frontend`
service deliberately does not, so the public-facing container never receives
`SECRET_KEY` or the database password — it gets only the two non-secret
values it needs:

| Variable            | Used by  | Critical? | Description                                   |
| -------------------- | -------- | --------- | ---------------------------------------------- |
| `POSTGRES_USER`      | database, backend | yes | Postgres role name |
| `POSTGRES_PASSWORD`  | database, backend | yes | Postgres role password |
| `POSTGRES_DB`        | database, backend | yes | Database name |
| `SECRET_KEY`         | backend  | yes       | Django `SECRET_KEY` / JWT signing secret |

Non-critical values already have sensible defaults baked into the Dockerfiles
and `docker-compose.yaml`. Override them in `.env` only if you need something
different:

| Variable                 | Default  | Description                                    |
| ------------------------- | -------- | ----------------------------------------------- |
| `BACKEND_PORT`             | `5000`   | Port Gunicorn listens on inside the container   |
| `BACKEND_HOST_PORT`        | `5000`   | Host port mapped to the backend (for direct API access/debugging) |
| `GUNICORN_WORKERS`         | `3`      | Number of Gunicorn worker processes             |
| `DEBUG`                    | `false`  | Django debug mode — keep `false` outside local dev |
| `ALLOWED_HOSTS`             | `*`      | Django `ALLOWED_HOSTS`. Defaults to `*` because the backend is only ever reached through the frontend's Nginx proxy, which forwards the original Host header (e.g. a Cloud VM's public IP) unchanged; set a comma-separated allowlist instead if the backend is ever exposed directly |
| `CORS_ORIGINS`             | `*`      | Allowed CORS origins for the API                |
| `FRONTEND_INTERNAL_PORT`   | `80`     | Port Nginx listens on inside the frontend container |

Anything left commented out in `.env` is simply not passed into the container,
so the default baked into the corresponding Dockerfile applies. The one place
`.env` values still have to be interpolated with `${...}` rather than supplied
through `env_file` is the `ports:` mappings: Compose resolves those while
parsing the file, before any container exists to read an environment from.

`DB_HOST` (`database`) and `DB_PORT` (`5432`) are set in `docker-compose.yaml`
rather than `.env`, since they describe the Compose network topology rather
than anything a user configures. The backend uses them both to build its
Django `DATABASES` setting and to poll the database from `entrypoint.sh`.

The frontend is always published on **host port 8282** (mapped to
`FRONTEND_INTERNAL_PORT` inside the container), independent of the internal
port configuration.

### Docker images

Both Dockerfiles use **multi-stage builds** to keep final images small and
free of build tooling:

- **`backend/Dockerfile`**: stage 1 (`builder`, `python:3.5-slim`) installs
  Python dependencies into a virtualenv; stage 2 (`runtime`) copies only that
  virtualenv and the application code into a fresh slim image, adds
  `postgresql-client` for `pg_isready`, runs as a non-root user, and starts
  via `entrypoint.sh` → Gunicorn (WSGI), never `manage.py runserver`. The
  Python 3.5 base is dictated by the unchanged Django 1.10 pin.
- **`frontend/Dockerfile`**: stage 1 (`build`, `node:20-alpine`) runs
  `npm install && npm run build` to produce a static Angular production
  bundle; stage 2 (`runtime`, `nginx:1.27-alpine`) copies only the built
  `dist/angular-conduit/` output and serves it with Nginx — no Node.js, no
  dev server, and no source code in the final image.

### docker-compose services

`docker-compose.yaml` defines three services — `frontend`, `backend`,
`database` — plus a named volume for Postgres data.

- All three services use `restart: unless-stopped`, so they come back
  automatically after a crash or host reboot.
- `backend` waits for `database` to report healthy (via a `pg_isready`
  healthcheck) before starting; `frontend` waits for `backend` to report
  healthy (via a request to `/api/tags`) before starting.
- `backend/entrypoint.sh` additionally polls the database with `pg_isready`
  in a loop before running migrations, so the backend still starts correctly
  if it is launched without Compose's health gating, or if the database
  restarts underneath it.
- The frontend's Nginx config resolves the backend hostname **per-request**
  via Docker's embedded DNS resolver, rather than once at startup — this
  means Nginx won't crash if it starts slightly before the backend, and it
  keeps working if the backend container is later recreated with a new IP.

### Changing the backend

The Django app lives in `backend/conduit/`:

- `apps/authentication/` — custom `User` model, JWT issuance/verification
  (`Authorization: Token <jwt>` header scheme, per the RealWorld spec).
- `apps/profiles/` — `Profile` model (bio, image, follows, favorites).
- `apps/articles/` — `Article`, `Comment`, `Tag` models and views.
- `apps/core/` — shared response rendering (`renderers.py`, wraps every
  response in the RealWorld envelope) and error handling (`exceptions.py`).
- `settings.py` — reads all configuration from environment variables;
  `SECRET_KEY` and the `POSTGRES_*` credentials raise at startup if missing
  (no silent fallback for secrets).

Database schema changes go through Django's migration system
(`python manage.py makemigrations` / `migrate`) — `entrypoint.sh` runs
`manage.py migrate --noinput` automatically on every container start.

To add a new endpoint: add a view to the relevant app's `views.py` and wire
it up in that app's `urls.py`, extending `models.py`/`serializers.py` as
needed. Restart with `docker compose up -d --build backend` to rebuild and
pick up the change.

### Changing the frontend

The Angular app lives in `frontend/src/app/`:

- `features/` — one module per feature area (article, profile, settings),
  each with its own routes/components/services.
- `core/services/` — shared API clients (articles, auth, profiles, tags).
- `core/interceptors/api.interceptor.ts` — rewrites every HTTP request to a
  **relative** `/api/...` URL (never an absolute backend URL — see below).
- `core/interceptors/token.interceptor.ts` — attaches the stored JWT as
  `Authorization: Token <jwt>` to outgoing requests.

In production, Nginx proxies `/api` to the `backend` container, so no
backend URL ever needs to be baked into the frontend build.

To run the frontend with hot reload against a locally running backend:
```bash
cd frontend
npm install
npm start
```
(`ng serve` has no API proxy configured out of the box — add a
`proxy.conf.json` if you want to avoid CORS during local dev, or just make
sure the backend's `CORS_ORIGINS` includes `http://localhost:4200`.)

To rebuild just the frontend image after a change:
```bash
docker compose up -d --build frontend
```

### Database and data persistence

Postgres data is stored in the named volume `postgres_data`, mounted at
`/var/lib/postgresql/data` in the `database` container. Data survives
`docker compose down` and container restarts; it is only removed if you
explicitly run `docker compose down -v` or delete the volume.

### Viewing and persisting logs

View logs for any service live:
```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f database
```

Persist a service's logs to a file for later review:
```bash
docker logs conduit-container-backend-1 > meine-container-logs.txt
```
(replace the container name with the actual name from `docker compose ps`).

## Security notes

- No SSH keys, passwords, tokens, or IP addresses are committed to this
  repository.
- `.env` (holding `POSTGRES_PASSWORD` and `SECRET_KEY`) is gitignored; only
  `.env.example`, with placeholder values, is committed.
- `docker-compose.yaml` never hardcodes credentials — it loads them from your
  local `.env` via `env_file`, and only for the services that need them.