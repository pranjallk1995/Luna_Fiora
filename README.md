# Luna Fiora

![Status: not yet usable](https://img.shields.io/badge/Status-not_yet_usable-D73A49)

> **Work in progress:** Luna Fiora is a private, local-first and desktop-first personal finance tracker.

Luna Fiora follows the Luna Visia, Vita, and Lumia architecture: React UI,
FastMCP/Python service, a database in Luna Sentia's shared PostgreSQL, single sign-on through Luna Sentia, and the shared
`luna_sentia_network` created by [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia).

> **Requires Luna Sentia, running and healthy:** Luna Fiora keeps its data in Luna Sentia's PostgreSQL (`luna-sentia-db`) and joins Sentia's `luna_sentia_network`; it has no database of its own. Start [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia) first and wait until its `postgres` and `ollama` services report healthy, as described under [Start](#start).

## Features

- Monthly income, expenditure, net savings, category, and cash-flow analytics.
- Custom date ranges, defaulting to the current month.
- Manual and Gmail-imported income and expense transactions.
- EMI and SIP tracking, reminders, and financial goals.
- Required monthly-saving estimates for goals.
- Read-only Gmail OAuth with periodic filtered transaction searches.
- Read-only Google Drive import of statements from a folder, as transactions.
- Deterministic bank-message parsing first; ambiguous messages use the local
  `qwen3-vl:8b-instruct` Ollama model served by Luna Sentia. Each message runs through a
  LangGraph graph (`mcp/app/services/import_graph.py`): already imported →
  skip; otherwise parse, ask the model only if parsing fails, then import or
  record for review.
- MCP tools for transactions, EMIs, SIPs, goals, reminders, analytics, and Gmail sync.

## Users and separate storage

Each person signs in with Google and has their own space in Luna Fiora: the schema `u_<id>` in the `lunafiora` database. It is created the first time they use the app. The owner adds, disables, and deletes people at Luna Sentia's `/admin`, and can hide this app from everyone else there; see [Users and separate storage](https://github.com/pranjallk1995/Luna_Sentia#users-and-separate-storage).

### Connecting an MCP client

Add `https://<your fiora MCP host>/mcp` to your client, such as Claude or ChatGPT, as a custom connector using OAuth. The client signs you in with Google and shows an approval page; check the return address, then allow it. Its tools then act only on your data. A request without a valid token gets 401.

Each person connects their own Gmail and Google Drive, and imports go to their own data. Gmail's read-only access needs Google's approval: while the Google client's consent screen is in Testing, add each person as a test user. Deleting someone removes their stored Gmail and Drive tokens here; they revoke the access itself in their Google account.

In the code, `mcp/app/core/tenancy.py` holds who the current request or job acts for, `mcp/app/data/tenants.py` creates and removes each person's schema, and `mcp/app/transport/luna_mcp.py` checks connector tokens and the private token on `/api/` routes. Code that does not say who it acts for raises `NoUserError` rather than reading anyone's data.

## Architecture

### Luna ecosystem

![Luna ecosystem architecture](docs/luna-ecosystem.svg)

Every Luna app is a React UI plus a FastMCP service on Luna Sentia's
`luna_sentia_network`: its data lives in Sentia's PostgreSQL, people sign in
through Sentia's `auth`, and model calls go through Sentia's model monitor, which times each one and samples the GPU, to its Ollama. Visia's SigLIP 2 image
embeddings and Vibia's CLAP music embeddings run inside those apps instead. Orange lines are
Visia image URLs that other apps use: food images for Vita, room images for
Lumia, and cover art for Vibia. Grey dashed lines are planned: links into Fiora
(tax details from Lexia, transaction image and icon URLs from Visia). Luna Unia
is the one home for all of them, on port 42069: it checks which Luna stacks are
running and opens each one with the shared sign-in. The purple line is the mood and
beats of the track Vibia plays, which Lumia's lights follow.

```text
React UI (through its gateway) or MCP client
        -> Luna Fiora MCP/API
        -> PostgreSQL
        -> Gmail and Google Drive APIs (read-only)
        -> Luna Sentia Ollama only when deterministic parsing is inconclusive
```

Fiora uses unique aliases `luna-fiora-mcp` and `luna-fiora-ui`. Its database lives in Luna Sentia's PostgreSQL (`luna-sentia-db`), which is private, and the service binds only to localhost.

## Start

Start [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia) first and wait until it is healthy. Sentia runs
the PostgreSQL server that holds Fiora's `lunafiora` database, serves the models,
and creates the shared `luna_sentia_network` every Luna app joins. Fiora has no
database of its own: started before Sentia is healthy, it cannot reach its
data and keeps restarting until it can.

```sh
cd ../Luna_Sentia
docker compose up -d --wait postgres ollama adminer
docker compose run --rm postgres-init   # creates the lunafiora role and database
docker compose ps                       # postgres and ollama must show (healthy)
```

See [Is Sentia healthy?](https://github.com/pranjallk1995/Luna_Sentia#is-sentia-healthy) if they do not.

To start Sentia and every Luna app together, with or without Compose Watch, use
`../luna.sh start [--watch]`; see the
[Sentia README](https://github.com/pranjallk1995/Luna_Sentia#start-everything).

Fiora reaches Ollama at `http://luna-sentia-ollama:11434` (override with
`OLLAMA_URL`). `OLLAMA_MODEL` must be one of the models in Sentia's
`SENTIA_MODELS`.

Create a private `.env` from `.env.example`.

Fiora signs people in through Luna Sentia's single sign-on: one Google sign-in at
Sentia opens every Luna app, and **Sign out** in any app signs out of all of them.
The UI needs no Google client of its own. Set `LUNA_SSO_URL` to
Sentia's public sign-on address (`SENTIA_AUTH_PUBLIC_URL` in Sentia's `.env`),
`LUNA_SSO_INTERNAL_URL` to `http://luna-sentia-auth:8000`, and
`LUNAFIORA_ALLOWED_EMAILS` to `*` for everyone with a Luna account, or to a comma-separated list; see
[Single sign-on](https://github.com/pranjallk1995/Luna_Sentia#single-sign-on).

### Gmail import

Gmail import needs a Google OAuth client, set as `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` in `.env`; Sentia's sign-on client works. In Google Cloud,

1. Enable the **Gmail API**.
2. Add `<MCP_PUBLIC_URL>/api/gmail/callback` to the client's redirect URIs.
3. Set the consent screen to **In production** (in *Testing*, Google expires the token after 7 days).

Then choose **Overview → Connect Gmail**. If Google later ends the sign-in, Fiora says so
and offers **Reconnect Gmail**; your transactions stay. Refresh tokens are encrypted at
rest with a key derived from `LUNAFIORA_API_TOKEN`, so changing that token means
reconnecting Gmail. Fiora requests only `https://www.googleapis.com/auth/gmail.readonly`.
OAuth credentials and tokens remain private and must never be committed.

### Google Drive import

Drive import uses the same Google client, with a separate sign-in that asks only for
`drive.readonly`. On that client's project, enable the **Google Drive API** and add
`<MCP_PUBLIC_URL>/api/drive/callback` to the redirect URIs. Then choose
**Overview → Connect Google Drive**, pick a folder, and import it.

Fiora reads PDFs with text, CSV, plain text, and Google Sheets; scans and Excel files are
reported, not read. The local model lists each statement's transactions, and a file's rows
are added together or not at all. Running a folder again skips files imported unchanged and
retries the rest. Balances, totals, and card bill payments are left out by name. A row with the same day, amount, and direction as one Fiora already has is
counted as **matched** and left out, so a statement does not double what Gmail imported, but
a genuine second payment of the same amount that day is left out too. A Gmail alert arriving
after its statement was imported is not matched. A locked PDF needs the password
given on the import, which stays in memory for the job and is not stored. Model-read rows can be wrong, so check an
import's first few transactions against the statement.

```sh
docker compose up --build
```

- UI: <http://127.0.0.1:18504>
- Health: <http://127.0.0.1:18003/health>
- MCP: <http://127.0.0.1:18003/mcp> (clients sign in; see Connecting an MCP client)

## Development workflow

Run Compose Watch in the foreground:

```sh
docker compose up --build --watch
```

Changes under `mcp/app/` synchronize and restart the MCP service. Changes to
`ui/gateway.py` and the other gateway files synchronize and restart the gateway.
Changes under `ui/web/src` rebuild the UI image, because the browser app is built
into it; for hot reload, run `npm run dev` in `ui/web`. Changes to either service's
requirements or Dockerfile rebuild that service. Generated Python caches are
excluded from sync.

## UI

The UI is a React and TypeScript app built with Vite, served by a small Starlette
gateway in `ui/gateway.py`. The gateway checks the shared Luna session and
`LUNAFIORA_ALLOWED_EMAILS` on every data request, and forwards only the backend
routes the UI uses, adding the private API token, which never reaches the browser.
Gateway tests run with `python -m unittest discover -s tests` in `ui/`, and browser
tests with `npm test` in `ui/web/`.

## MCP tools

- Web UI: `get_ui_link`
- Transactions: `list_transactions`, `add_transaction`, `update_transaction`,
  `delete_transaction`
- EMIs and SIPs: `list_commitments`, `create_commitment`,
  `update_commitment`, `delete_commitment`
- Goals: `list_goals`, `create_goal`, `update_goal`, `delete_goal`,
  `estimate_goal_savings`
- Reminders: `list_reminders`, `create_reminder`, `update_reminder`,
  `delete_reminder`
- Analytics and Gmail imports: `financial_analytics`, `gmail_status`,
  `sync_gmail_transactions`
- Google Drive: `google_drive_status`, `list_drive_folders`, `import_drive_folder`,
  `get_drive_import_job`, `list_drive_import_jobs`

## Database UI

Fiora's database is in Luna Sentia's PostgreSQL, which is not published to the host. Inspect it with
[Adminer in Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia#database-ui) at
<http://127.0.0.1:19080>: System `PostgreSQL`, Server `luna-sentia-db`, Username
and Database `lunafiora`, Password your `POSTGRES_PASSWORD`.

## Privacy boundaries

Gmail queries are restricted to recent transaction-like messages. Unknown
messages are not treated as transactions automatically. The local Ollama prompt
is instructed to ignore email instructions and return structured transaction
data only. Imported Gmail excerpts are limited to 500 characters for review and
deduplication; full email bodies are not stored.
