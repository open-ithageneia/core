# core

Install [nvm](https://github.com/nvm-sh/nvm) and run `nvm use`.

Install npm dependencies with `npm install`

Create a `.env` file and add a `SECRET_KEY`.

In separate terminals, run:

* `npm run dev`
* `uv run python manage.py runserver 0.0.0.0:8000`

All python commands you muse prefix with `uv run` to make sure the correct virtual env is used.