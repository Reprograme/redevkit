# Dev command and port detection

Use the first source that answers; state which one was used.

## 1. Memory

`.redevkit/memory/tech.md` › Development environment: dev command and preview port.

## 2. Package scripts (Node)

- Package manager by lockfile: `pnpm-lock.yaml` → `pnpm`, `yarn.lock` → `yarn`,
  `bun.lockb` or `bun.lock` → `bun`, otherwise `npm`.
- Script, first found in `package.json` › `scripts`: `dev`, `start`, `preview`, `serve`.
- Command: `<pm> run <script>`. A port passed in the script (`--port 4000`, `-p 4000`,
  `PORT=4000`) wins over the framework default.

## 3. Framework conventions

| Signal | Dev command | Default port | Port flag |
| --- | --- | --- | --- |
| `next` dependency | `<pm> run dev` | 3000 | `-- -p <port>` |
| `vite` dependency | `<pm> run dev` | 5173 | `-- --port <port>` |
| `astro` dependency | `<pm> run dev` | 4321 | `-- --port <port>` |
| `@angular/core` | `<pm> run start` | 4200 | `-- --port <port>` |
| `nuxt` dependency | `<pm> run dev` | 3000 | `-- --port <port>` |
| `@sveltejs/kit` | `<pm> run dev` | 5173 | `-- --port <port>` |
| `react-scripts` | `<pm> run start` | 3000 | env `PORT=<port>` |
| `expo` (web) | `npx expo start --web` | 8081 | `--port <port>` |
| Django `manage.py` | `python manage.py runserver` | 8000 | `runserver <port>` |
| Flask app | `flask run` | 5000 | `--port <port>` |
| FastAPI with uvicorn | `uvicorn <module>:app --reload` | 8000 | `--port <port>` |
| Rails `bin/rails` | `bin/rails server` | 3000 | `-p <port>` |
| Phoenix `mix.exs` | `mix phx.server` | 4000 | env `PORT=<port>` |
| Static `index.html` only | `npx serve .` | 3000 | `-l <port>` |

## 4. Ask

Nothing found: ask for the dev command and port, with the most likely candidate as the
recommendation. Suggest saving the answer in `tech.md` through the memory skill; the preview
itself never writes memory.
