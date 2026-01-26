# Open Ithageneia (core)

Django + Inertia.js + React (Vite) + Tailwind + shadcn/ui.

## Prerequisites

### Python (UV)

- Python: **3.12+** (see `.python-version`)
- Package manager: **uv**

Install uv:

Linux/macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Node (nvm)

- Node is managed via **nvm** (see `.nvmrc`).

Install nvm: https://github.com/nvm-sh/nvm

Then, from the repo root:

```bash
nvm install
nvm use
```

## Local development

### 1) Install dependencies

Python deps (creates/updates `.venv`):

```bash
uv sync
```

Node deps:

```bash
npm install
```

### 2) Configure environment variables

Create a `.env` file in the project root (you can start from `.env.example`).

Minimum required:

```env
SECRET_KEY=replace-me
DEBUG=True
```

Optional:

```env
# Vite dev server settings used by django-vite
DJANGO_VITE_DEV_SERVER_HOST=localhost
DJANGO_VITE_DEV_SERVER_PORT=5173
```

### 3) Run migrations

```bash
uv run python manage.py migrate
```

### 4) Start the dev servers

You need **two terminals** in development:

Terminal A (Vite + HMR):

```bash
npm run dev
```

Terminal B (Django):

```bash
uv run python manage.py runserver 0.0.0.0:8000
```

Open http://localhost:8000

### Useful commands

- TypeScript typecheck: `npm run typecheck`
- Frontend production build: `npm run build`
- Create admin user: `uv run python manage.py createsuperuser`

## Linting and formatting

If you just want the “project standard” commands, use:

- Lint everything: `make lint`
- Auto-fix everything: `make fix`

### Python (Ruff)

Ruff is used for Python linting and formatting. It’s included in the project’s dev dependencies, so it is installed automatically when you run `uv sync` (unless you pass `--no-dev`).

- Lint: `uv run ruff check .`
- Lint + auto-fix: `uv run ruff check --fix .`
- Format: `uv run ruff format .`

Editor setup: https://docs.astral.sh/ruff/editors/setup/

### JavaScript/TypeScript (Biome)

Biome is used for JS/TS linting and formatting.

- Lint: `npm run lint`
- Lint/format + auto-fix: `npm run biome:fix`

Editor setup: https://biomejs.dev/guides/editors/first-party-extensions/

## shadcn/ui

shadcn/ui is configured via `components.json`:

- TSX output is enabled (`"tsx": true`).
- Aliases are wired to `@/…` and resolve to `frontend/js/…`.

### Add a component

From the repo root:

```bash
npx shadcn@latest add button
```

This will generate components under `frontend/js/components/ui/`.

### Update/overwrite an existing component

shadcn/ui doesn’t automatically “upgrade all components”; the usual flow is to re-add a component and overwrite after reviewing changes:

```bash
npx shadcn@latest add alert-dialog --overwrite
```

If your installed CLI uses the older package name, use `npx shadcn-ui@latest …` instead.

## Notes

- Always prefix Python commands with `uv run` to use the project’s virtual environment.
- SQLite is used by default (`db/db.sqlite3`).

## Deployment & production

### Environment variables

This project loads environment variables from `.env` in the repo root (see `.env.example`).

| Name | Required | Default | Notes |
| --- | --- | --- | --- |
| `DJANGO_SETTINGS_MODULE` | No | - | Optional. Set to `open_ithageneia.settings_production` for production defaults. |
| `SECRET_KEY` | Yes | - | Django secret key. Use a strong value in production. |
| `DEBUG` | No | `True` | Used by `open_ithageneia.settings`. Production settings force `DEBUG=False`. |
| `ALLOWED_HOSTS` | No | `*` | Comma-separated list in dev. Production defaults to an empty list and should be set explicitly. |
| `CSRF_TRUSTED_ORIGINS` | No | `[]` | Comma-separated list. Often required in production. |
| `DJANGO_VITE_DEV_SERVER_HOST` | No | `localhost` | Dev only (HMR). |
| `DJANGO_VITE_DEV_SERVER_PORT` | No | `5173` | Dev only (HMR). |
| `IS_PREVIEW_DEPLOYMENT` | No | `False` | Marks the current running container as a preview deployment. Set this only in preview environments. |
| `PREVIEW_SUPERUSER_USERNAME` | No | - | If set (with `PREVIEW_SUPERUSER_PASSWORD`), entrypoint runs `createsuperuser --noinput` on startup (preview-only). |
| `PREVIEW_SUPERUSER_PASSWORD` | No | - | Password for `PREVIEW_SUPERUSER_USERNAME` (preview-only). |
| `SQLITE_DB_FILENAME` | No | `db.sqlite3` | SQLite filename. |

### Preview deployments (SQLite)

If you deploy preview environments (PRs/branches) and still use SQLite, you generally want previews
to use a different DB so migrations don’t touch the production DB.

This repo also avoids persisting preview DBs: when a deployment is detected as a preview, the SQLite
file is placed under `/tmp/...` inside the container (so it’s cleaned up when the container is
destroyed), rather than under `db/` (which is typically mounted as a persistent volume).

This project supports that in a provider-agnostic way with explicit flags.

Recommended setup:

- In your preview deployment env vars, set:
	- `IS_PREVIEW_DEPLOYMENT=True`

When this is true, the SQLite file is stored under `/tmp/open_ithageneia_db/` inside the container.

#### Preview admin user (SQLite previews)

Since preview SQLite databases are ephemeral, you may want an admin user recreated on every start.

Set these in preview environments (they are ignored unless `IS_PREVIEW_DEPLOYMENT` is enabled):

```env
PREVIEW_SUPERUSER_USERNAME=admin
PREVIEW_SUPERUSER_PASSWORD=change-me
```

### Production build (Docker)

There is a multi-stage Docker build that:

1) installs Python deps with uv
2) builds the Vite frontend
3) runs Django with Gunicorn

Build:

```bash
docker build -t open-ithageneia .
```

Run production image locally (recommended):

```bash
./scripts/run_prod_local.sh
```
