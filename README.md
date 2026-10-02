# OneMoreRep

OneMoreRep is a web-based workout log and private friends community. It records strength, walking, and sports sessions; tracks daily weight and progress photos; awards EXP; and lets accepted friends share updates in a private feed.

## Local setup

Requirements: Python 3.12+, Node.js 20+, PostgreSQL 14+.

Create a virtual environment and install the Python packages (run these commands from the project folder):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks environment activation, run `Set-ExecutionPolicy -Scope Process Bypass` in that terminal, then activate the environment again. Install the website packages once:

```powershell
cd frontend
npm install
cd ..
```

This machine's local PostgreSQL binaries are configured from the path provided. The database cluster lives in `data/postgres`; its local credentials are held in ignored `config_local.py`. Start the app from this folder with:

```powershell
.\start_onemorerep.ps1
```

The script starts PostgreSQL if needed, starts the FastAPI API and Next.js website in the background, waits for both, then opens [http://127.0.0.1:3000](http://127.0.0.1:3000). Logs are written under `work/`. If frontend dependencies are missing, run `cd frontend; npm install` once.

For manual development, first activate `.venv` in both terminals. Use two terminals:

```powershell
# terminal 1, project root
python -m uvicorn onemorerep.webapp:app --host 127.0.0.1 --port 8000

# terminal 2
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. The API docs are at `http://127.0.0.1:8000/docs`.

## PostgreSQL setup and data

The app uses PostgreSQL through `psycopg`. It initializes an empty app schema if none exists and adds new tables/indexes safely. It never drops existing tables. You confirmed the existing MySQL instance had no data, so no migration was needed; that service was left unchanged and the PostgreSQL database configured here is the fresh app database.

Never delete `data/postgres`; it contains the local app database. Credentials come from `ONEMOREREP_DB_*` environment variables or the ignored local `config_local.py` fallback. Set `ONEMOREREP_COOKIE_SECURE=true` behind HTTPS and configure `ONEMOREREP_CORS_ORIGINS` for the deployed website origin.

For a separate PostgreSQL installation, create a UTF-8 database named `onemorerep`, install the packages above, then set `ONEMOREREP_DB_HOST`, `ONEMOREREP_DB_PORT`, `ONEMOREREP_DB_USER`, `ONEMOREREP_DB_PASSWORD`, and `ONEMOREREP_DB_NAME` in the shell before starting the API. The app inspects the PostgreSQL schema on startup; an empty schema is initialized, while a partial or incompatible existing schema causes a clear startup error without dropping tables.

## Features

- Register and sign in with bcrypt-hashed passwords and server-side sessions.
- Record strength, walking, and sports activities, with an optional private workout photo.
- Log daily weight, notes, and optional private fitness photos in progress reports.
- Earn capped morning/evening EXP and track activity streaks.
- Send, accept, and manage friend requests.
- Share workout summaries, selected workout photos, screenshots, or achievements in a feed limited to you and accepted friends.
- Like friends' posts and comment on them.
- Use role-based access control: regular accounts see their own private records, while administrator accounts can review, edit, and delete member records in a separate console.
- Browse history, EXP, leaderboard, statistics, and profile.

### Administrator access

New accounts always start with the `user` role. Promote an existing account from the project folder with:

```powershell
python -m onemorerep.admin your_username admin
```

The command uses the configured PostgreSQL database. Sign out and back in after changing a role; administrators then see the Admin item in the sidebar. Admin edit and delete routes independently enforce the role on every request. Account deletion removes that account's associated records and uploaded photos; the signed-in administrator and last admin account are protected from deletion. To revoke admin access, run the same command with `user` instead of `admin`.

Image uploads accept JPEG, PNG, or WebP up to 8 MB. Local uploads are stored under `uploads/`; use persistent/object storage when deploying.

## Tests

```powershell
python -m unittest discover -s tests -v
```

The business-rule tests do not require PostgreSQL. An additional integration test exercises duplicate-award protection and streak persistence inside a transaction that rolls back its test data. Run it against the local app database with:

```powershell
$env:ONEMOREREP_TEST_DATABASE = '1'
python -m unittest discover -s tests -v
```

## Deploying to Vercel

The repository has a Vercel ASGI entry point at `api/index.py`. Vercel builds the Next.js export, publishes its hashed JavaScript and CSS under the root `public/_next` CDN path, and FastAPI's `app.frontend()` serves the exported pages while API routes remain handled by FastAPI. The `.vercelignore` file excludes local database files, local credentials, and local uploads.

Before deploying, create a Supabase project and a **private** Storage bucket named `onemorerep-private` (or set another name in the environment). The app supports Supabase Storage for photos when enabled. Do not point Vercel at the PostgreSQL server running on your PC.

Configure these Vercel project environment variables for Production (and Preview if needed):

- `ONEMOREREP_DB_HOST`, `ONEMOREREP_DB_PORT`, `ONEMOREREP_DB_USER`, `ONEMOREREP_DB_PASSWORD`, `ONEMOREREP_DB_NAME` for the hosted PostgreSQL database.
- `ONEMOREREP_MEDIA_STORAGE=supabase`, `SUPABASE_URL`, `SUPABASE_SECRET_KEY`, and optionally `SUPABASE_STORAGE_BUCKET=onemorerep-private` for private image storage. Keep the secret key only as a server environment variable; never add it to frontend `NEXT_PUBLIC_*` variables.
- `ONEMOREREP_COOKIE_SECURE=true` so sign-in cookies are sent only over HTTPS.
- `ONEMOREREP_CORS_ORIGINS` set to the exact deployed site origin if frontend and API are later split across different domains. With the included same-origin `/api/*` routing, cross-origin requests are not needed.
- `NEXT_PUBLIC_API_URL` can be omitted for the included same-origin routing. Set it to the API origin if the frontend is deployed separately.

Use the PostgreSQL **Transaction pooler** values from Supabase for Vercel serverless use. The app disables Psycopg automatic prepared statements for compatibility with transaction pooling. The FastAPI startup initializes the schema on first connection. After the first deployment, register an account and promote it through the database or a one-time trusted administrative environment; do not expose local database credentials or `config_local.py` in the deployment.

Vercel deployment still requires linking this folder to a Vercel project and signing in with a Vercel account. Once the Supabase project and private bucket are ready, add the environment variables above, then deploy from this folder using Vercel CLI or import the repository into Vercel.
