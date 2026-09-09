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
- [Deployment](#deployment)
  - [How the pipeline works](#how-the-pipeline-works)
  - [One-time setup](#one-time-setup)
  - [Required secrets and variables](#required-secrets-and-variables)
  - [Running and troubleshooting a deployment](#running-and-troubleshooting-a-deployment)
  - [Changing the deployment workflow](#changing-the-deployment-workflow)
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

`--build` builds the images locally, which works because
`docker-compose.override.yaml` is present in a checkout. Without `--build`, the
images are pulled from the registry instead. To deploy this to a server, see
[Deployment](#deployment) — deployments are automatic on a push to `main`.


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
`api.realworld.io` demo API.

On top of the containers, the repository carries its own delivery pipeline:
[`.github/workflows/deployment.yaml`](.github/workflows/deployment.yaml) builds
both images on GitHub's runners, publishes them to the GitHub Container
Registry, and deploys them to a cloud VM over SSH with `docker compose` in
detached mode. The VM only ever pulls prebuilt images — see
[Deployment](#deployment).

The purpose of this repository is not to demonstrate novel product features,
but to show a correct, secure, production-shaped containerization and
deployment of a full-stack app: multi-stage Dockerfiles, environment-based
configuration, crash-resilient services, an automated SSH deployment, and a
documented developer workflow.

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
├── .github/workflows/
│   └── deployment.yaml         CI/CD: builds + pushes images, deploys over SSH
├── docker-compose.yaml        Orchestrates frontend + backend + database (registry images)
├── docker-compose.override.yaml  Local-only: adds the `build:` sections back in
├── .env.example                Template for required environment variables
└── README.md
```

`docker-compose.yaml` is the file that is copied to the cloud VM, and it
references prebuilt registry images only. `docker-compose.override.yaml` is
merged in automatically by `docker compose` when you work locally, and is the
only place a `build:` section exists — so the VM can never accidentally build
an image. See [Deployment](#deployment).

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
| `BACKEND_HOST_PORT`        | `5000`   | Host port mapped to the backend for direct API access while developing. Local only — the deployed stack does not publish this port |
| `GUNICORN_WORKERS`         | `3`      | Number of Gunicorn worker processes             |
| `DEBUG`                    | `false`  | Django debug mode — keep `false` outside local dev |
| `ALLOWED_HOSTS`             | `*`      | Django `ALLOWED_HOSTS`. Defaults to `*` because the backend is only ever reached through the frontend's Nginx proxy, which forwards the original Host header (e.g. a Cloud VM's public IP) unchanged; set a comma-separated allowlist instead if the backend is ever exposed directly |
| `CORS_ORIGINS`             | `*`      | Allowed CORS origins for the API                |
| `FRONTEND_INTERNAL_PORT`   | `80`     | Port Nginx listens on inside the frontend container |
| `FRONTEND_HOST_PORT`       | `8282`   | Host port the app is published on — the checklist requires `8282` |
| `IMAGE_REGISTRY`           | `ghcr.io/mshaninah` | Registry namespace the `backend`/`frontend` images are pulled from |
| `IMAGE_TAG`                | `latest` | Image tag to run. The deployment workflow pins this to the deployed commit SHA |
| `LOG_MAX_SIZE`             | `10m`    | Max size of a single container log file before it is rotated |
| `LOG_MAX_FILE`             | `5`      | Number of rotated log files kept per container |

Anything left commented out in `.env` is simply not passed into the container,
so the default baked into the corresponding Dockerfile applies. The one place
`.env` values still have to be interpolated with `${...}` rather than supplied
through `env_file` is the `ports:` mappings: Compose resolves those while
parsing the file, before any container exists to read an environment from.

`DB_HOST` (`database`) and `DB_PORT` (`5432`) are set in `docker-compose.yaml`
rather than `.env`, since they describe the Compose network topology rather
than anything a user configures. The backend uses them both to build its
Django `DATABASES` setting and to poll the database from `entrypoint.sh`.

The frontend is published on **host port 8282** by default (mapped to
`FRONTEND_INTERNAL_PORT` inside the container), independent of the internal
port configuration. Override `FRONTEND_HOST_PORT` only if 8282 is unavailable.

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

Images are built once, by CI, and published to the GitHub Container Registry as
`ghcr.io/<owner>/conduit-backend` and `ghcr.io/<owner>/conduit-frontend`, each
tagged with both `latest` and the commit SHA it was built from. The cloud VM
pulls those images; it never builds them. Locally, `docker compose build` (or
`up --build`) still builds from source thanks to `docker-compose.override.yaml`.

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
- Only the `frontend` publishes a port in the deployed stack. The backend is
  reachable exclusively through Nginx's `/api` proxy on the internal Compose
  network; `docker-compose.override.yaml` publishes `BACKEND_HOST_PORT` locally
  so you can call the API directly while developing.
- Every service logs through the `json-file` driver with rotation configured
  (`LOG_MAX_SIZE`, `LOG_MAX_FILE`), so container logs stay readable via the CLI
  without filling the VM's disk.

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
docker compose logs --no-color --timestamps backend > backend-logs.txt
```
Or, for a single container by name (get the name from `docker compose ps`):
```bash
docker logs conduit-container-backend-1 > backend-logs.txt
```

All services use the `json-file` logging driver with rotation, so Docker itself
also persists the logs on disk (under `/var/lib/docker/containers/<id>/`) and
caps them: `LOG_MAX_SIZE` (default `10m`) per file, `LOG_MAX_FILE` (default `5`)
files per container. Raise those in `.env` if you need a longer history:
```bash
LOG_MAX_SIZE=50m
LOG_MAX_FILE=10
```

## Deployment

Pushing to `main` builds, publishes and deploys the application automatically.
The workflow lives in [`.github/workflows/deployment.yaml`](.github/workflows/deployment.yaml).

### How the pipeline works

```
push to main ──▶ build-and-push (GitHub runner)      ──▶ deploy (over SSH)
                 ├── build backend image                 ├── scp docker-compose.yaml → VM
                 ├── build frontend image                ├── write .env from secrets
                 └── push both to ghcr.io                ├── docker login ghcr.io
                     (tags: <commit-sha>, latest)        ├── docker compose pull
                                                         ├── docker compose up --detach --wait
                                                         └── smoke test :8282 + :8282/api/tags
```

Two design points worth calling out:

- **Nothing is built on the VM.** Both images are built on GitHub's runners and
  pushed to the GitHub Container Registry (GHCR). The VM receives only
  `docker-compose.yaml`, which contains no `build:` sections, and pulls the
  finished images. This keeps the VM small, makes deploys fast, and means the
  VM needs neither the source code nor a build toolchain.
- **The workflow fails loudly.** Every remote step runs with `script_stops:
  true` and `set -eu`, `docker compose up` uses `--wait` (which blocks until
  every container reports healthy and exits non-zero if one does not), and a
  final step curls the frontend and the proxied API. Any failure anywhere marks
  the workflow run as failed.

Each deploy pins `IMAGE_TAG` to the exact commit SHA that was just built, so a
deployment is reproducible and you can always see which commit is running.

### One-time setup

**On the cloud VM:**

1. Install Docker Engine with the Compose plugin (`docker compose version`
   must report v2.17 or newer, for `docker compose up --wait`) and `curl`.
2. Make sure the deploy user can run Docker without `sudo`:
   ```bash
   sudo usermod -aG docker "${USER}"
   ```
   (log out and back in afterwards)
3. Create the deployment directory — `~/conduit` unless you set the
   `DEPLOY_PATH` repository variable:
   ```bash
   mkdir -p ~/conduit
   ```
4. Open port `8282` in the VM's firewall / cloud security group.
5. Add the public half of your deploy key to `~/.ssh/authorized_keys`.

**In the GitHub repository** (Settings → Secrets and variables → Actions), add
the secrets and variables listed below.

**On GHCR:** the workflow pushes with the automatically provided
`GITHUB_TOKEN`, so no personal access token is needed. The same token is passed
to the VM for the duration of the run so it can `docker login ghcr.io` and pull
private packages. If you'd rather not do that, make the two packages public
under your GitHub profile → Packages → Package settings, and the pull works
anonymously.

### Required secrets and variables

Secrets (Settings → Secrets and variables → Actions → **Secrets**):

| Secret              | Description                                                   |
| -------------------- | -------------------------------------------------------------- |
| `SSH_HOST`           | Public IP or hostname of the cloud VM                          |
| `SSH_USER`           | SSH login user on the VM                                       |
| `SSH_PRIVATE_KEY`    | Private half of the deploy key, whole PEM block including headers |
| `SSH_PORT`           | Optional. SSH port; defaults to `22` if unset                  |
| `POSTGRES_USER`      | Postgres role name written into the VM's `.env`                |
| `POSTGRES_PASSWORD`  | Postgres role password                                         |
| `POSTGRES_DB`        | Database name                                                  |
| `SECRET_KEY`         | Django `SECRET_KEY` / JWT signing secret                       |

Variables (same page, **Variables** tab) — all optional:

| Variable             | Default     | Description                              |
| --------------------- | ----------- | ----------------------------------------- |
| `DEPLOY_PATH`         | `~/conduit` | Directory on the VM holding the compose file and `.env` |
| `FRONTEND_HOST_PORT`  | `8282`      | Host port the app is published on         |

The VM's `.env` is rewritten from these secrets on **every** deploy, so
credentials exist only in GitHub's secret store and on the VM's filesystem
(created with `umask 077`) — never in git, never in an image layer, and never
in the workflow logs.

### Running and troubleshooting a deployment

A push to `main` deploys automatically. To deploy the current `main` without
pushing, use **Actions → Deployment → Run workflow** (the workflow declares
`workflow_dispatch`).

Once deployed, the app is reachable at `http://<vm-ip>:8282`.

Useful checks on the VM:

```bash
cd ~/conduit
docker compose ps                 # which images/tags are running, and health
docker compose logs -f backend    # follow a service's logs
docker compose config             # the fully resolved configuration
```

Common failures:

- **`docker compose up --wait` times out** — a container never became healthy.
  Run `docker compose ps` and `docker compose logs <service>` on the VM; the
  backend is usually the culprit (a bad `SECRET_KEY` or database credentials).
- **`denied` / `unauthorized` on `docker compose pull`** — the packages are
  private and the registry login failed. Confirm the `packages: read`
  permission on the `deploy` job, or make the packages public.
- **The smoke test fails but the containers are healthy** — check that
  `FRONTEND_HOST_PORT` matches the port you opened in the firewall.

### Changing the deployment workflow

- **Deploy from a different branch:** change the `on.push.branches` list at the
  top of `.github/workflows/deployment.yaml`.
- **Deploy to a different registry:** change the `IMAGE_REGISTRY` value in the
  workflow's top-level `env:` block (it is used for both the login and the image
  tags), and the `IMAGE_REGISTRY` default in `docker-compose.yaml`.
- **Add a service to the stack:** add it to `docker-compose.yaml`. If it needs
  building, add it to the `matrix.service` list in the `build-and-push` job and
  to `docker-compose.override.yaml`.
- **Deploy a specific version rather than the newest commit:** override
  `IMAGE_TAG` in the VM's `.env` and run `docker compose up -d` there, or change
  the `IMAGE_TAG` env value in the workflow's deploy step.
- **Roll back:** re-run an older successful workflow run from the Actions tab —
  it redeploys that run's commit SHA.

## Security notes

- No SSH keys, passwords, tokens, or IP addresses are committed to this
  repository.
- `.env` (holding `POSTGRES_PASSWORD` and `SECRET_KEY`) is gitignored; only
  `.env.example`, with placeholder values, is committed.
- `docker-compose.yaml` never hardcodes credentials — it loads them from your
  local `.env` via `env_file`, and only for the services that need them.
- The deployment workflow contains no host names, IP addresses, users or keys.
  Everything host-specific comes from GitHub Actions secrets and variables
  (see [Required secrets and variables](#required-secrets-and-variables)), so
  the repository stays publishable as-is.
- The SSH deploy key lives only in the `SSH_PRIVATE_KEY` secret. It is never
  written into the workspace, and secrets passed to the VM are masked in the
  workflow logs.
- The VM's `.env` is written with `umask 077`, so it is readable only by the
  deploy user.