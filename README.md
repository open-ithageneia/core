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

# Use Postgres/etc instead of sqlite
# DATABASE_URL=postgres://user:pass@localhost:5432/dbname
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
- SQLite is used by default (`db.sqlite3`). Set `DATABASE_URL` to use another database.

## Production build (Docker)

There is a multi-stage Docker build that:

1) installs Python deps with uv
2) builds the Vite frontend
3) runs Django with Gunicorn

Build:

```bash
docker build -f prod.Dockerfile -t open-ithageneia .
```

Run (example):

```bash
docker run --rm -p 8000:8000 \
	-e SECRET_KEY=replace-me \
	-e DEBUG=0 \
	open-ithageneia
```