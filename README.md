# core

## Setup (Python)

1. Install uv (once):
   https://astral.sh/uv

2. Create venv:
   uv venv

3. Install dependencies:
   uv pip install .

4. Run server:
   uv run python manage.py runserver (or uv run --env-file .env python manage.py runserver  if you have the secret key stored in .env file)
