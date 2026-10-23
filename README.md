# Luna Fiora

![Status: not yet usable](https://img.shields.io/badge/Status-not_yet_usable-D73A49)

> **Work in progress:** Luna Fiora is a private, local-first and desktop-first personal finance tracker.

Luna Fiora follows the Luna Visia, Vita, and Lumia architecture: Streamlit UI,
FastMCP/Python service, PostgreSQL, Google OIDC, and the shared
`luna_sentia_network` created by [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia).

## Features

- Monthly income, expenditure, net savings, category, and cash-flow analytics.
- Custom date ranges, defaulting to the current month.
- Manual and Gmail-imported income and expense transactions.
- EMI and SIP tracking, reminders, and financial goals.
- Required monthly-saving estimates for goals.
- Read-only Gmail OAuth with periodic filtered transaction searches.
- Deterministic bank-message parsing first; ambiguous messages use the local
  `qwen2.5vl:7b` Ollama model served by Luna Sentia.
- MCP tools for transactions, EMIs, SIPs, goals, reminders, analytics, and Gmail sync.

## Architecture

```text
Streamlit UI or MCP client
        -> Luna Fiora MCP/API
        -> PostgreSQL
        -> Gmail API (read-only)
        -> Luna Sentia Ollama only when deterministic parsing is inconclusive
```

Fiora uses unique aliases `luna-fiora-db`, `luna-fiora-mcp`, and
`luna-fiora-ui`. PostgreSQL is private and the service binds only to localhost.

## Start

Start [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia) first. It creates the shared external
`luna_sentia_network` that every Luna app joins:

```sh
cd ../Luna_Sentia && docker compose up -d
```

To start Sentia and every Luna app together, with or without Compose Watch, use
`../luna.sh start [--watch]`; see the
[Sentia README](https://github.com/pranjallk1995/Luna_Sentia#start-everything).

Fiora reaches Ollama at `http://luna-sentia-ollama:11434` (override with
`OLLAMA_URL`). `OLLAMA_MODEL` must be one of the models in Sentia's
`SENTIA_MODELS`.

Create a private `.env` from `.env.example`. Generate a Fernet key for
`FIORA_TOKEN_ENCRYPTION_KEY`; it encrypts Gmail refresh tokens at rest.

Create `ui/.streamlit/secrets.toml` from the example and configure normal Luna
Google sign-in:

- Hosted: `https://fiora.lunaapps.fyi/oauth2callback`
- Local: `http://localhost:18504/oauth2callback`

For Gmail import, enable the Gmail API in Google Cloud and add a separate backend callback:

- Hosted: `https://fiora-mcp.lunaapps.fyi/api/gmail/callback`
- Local: `http://localhost:18003/api/gmail/callback`

Set the selected URL as `GMAIL_REDIRECT_URI`. Fiora requests only
`https://www.googleapis.com/auth/gmail.readonly`. OAuth credentials and tokens
remain private and must never be committed.

```sh
docker compose up --build
```

- UI: <http://127.0.0.1:18504>
- Health: <http://127.0.0.1:18003/health>
- MCP: <http://127.0.0.1:18003/mcp>

## Development workflow

Run Compose Watch in the foreground:

```sh
docker compose up --build --watch
```

Changes under `mcp/app/` synchronize and restart the MCP service. UI source
changes synchronize without rebuilding so Streamlit reruns automatically.
Changes to either service's requirements or Dockerfile rebuild that service.
Private Streamlit secrets and generated Python caches are excluded from sync.
## MCP tools

- Transactions: `list_transactions`, `add_transaction`, `update_transaction`,
  `delete_transaction`
- EMIs and SIPs: `list_commitments`, `create_commitment`,
  `update_commitment`, `delete_commitment`
- Goals: `list_goals`, `create_goal`, `update_goal`, `delete_goal`,
  `estimate_goal_savings`
- Reminders: `list_reminders`, `create_reminder`, `update_reminder`,
  `delete_reminder`
- Analytics and imports: `financial_analytics`, `sync_gmail_transactions`

## Database UI

PostgreSQL is not published to the host. Inspect it with
[Adminer in Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia#database-ui) at
<http://127.0.0.1:19080>: System `PostgreSQL`, Server `luna-fiora-db`, Username
and Database `lunafiora`, Password your `POSTGRES_PASSWORD`.

## Privacy boundaries

Gmail queries are restricted to recent transaction-like messages. Unknown
messages are not treated as transactions automatically. The local Ollama prompt
is instructed to ignore email instructions and return structured transaction
data only. Imported Gmail excerpts are limited to 500 characters for review and
deduplication; full email bodies are not stored.
