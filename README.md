# Luna Fiora

![Docker required](https://img.shields.io/badge/Docker-required-2496ED?logo=docker&logoColor=white)
![Luna Sentia required](https://img.shields.io/badge/Luna_Sentia-required-6C5CE7?logo=docker&logoColor=white)
![Status: early access](https://img.shields.io/badge/Status-early_access-DB6D28)

> **Work in progress.**

**A private personal-finance tracker your AI assistant can keep up to date.** Fiora brings in your income and
spending from bank emails and statements, and tracks EMIs, SIPs, goals and reminders.

## What it does

- **Monthly analytics:** income, spending, net savings, categories and cash flow, for any date range.
- **Transactions** added by hand, from bank emails in Gmail, or from statements in a Google Drive folder (both
  read-only).
- **Rules first, model second:** known bank messages are parsed by rules; only the ones they can't read go to a local
  model, and anything unsure waits for your review.
- **EMIs, SIPs, goals and reminders**, with the monthly saving each goal needs.
- **Private by design:** only recent transaction-like emails are searched, and full email bodies are never stored.

## Quickstart

Fiora runs on [Luna Sentia](https://github.com/pranjallk1995/Luna_Sentia), which provides its database, model and
sign-in. On one machine you need no `.env`:

```sh
git clone https://github.com/pranjallk1995/Luna_Sentia.git
git clone https://github.com/pranjallk1995/Luna_Fiora.git
./Luna_Sentia/luna.sh start fiora
```

Open <http://localhost:18500> and sign in as Sentia's owner. Gmail and Drive imports need a Google client, and a
public address needs your own secrets: see [Getting started](https://github.com/pranjallk1995/Luna_Fiora/wiki/Getting-Started).

## Connect your AI assistant

Add `https://<your fiora MCP host>/mcp` to Claude, ChatGPT or any MCP client as a custom connector (OAuth). Every
tool is listed in [MCP tools](https://github.com/pranjallk1995/Luna_Fiora/wiki/MCP-Tools).

## Works with

- **[Luna Lexia](https://github.com/pranjallk1995/Luna_Lexia)** (planned): tax and salary details from your documents.

## Documentation

The [wiki](https://github.com/pranjallk1995/Luna_Fiora/wiki) has the full reference:

| Page | What's in it |
| --- | --- |
| [Home](https://github.com/pranjallk1995/Luna_Fiora/wiki) | Features and the UI |
| [Getting started](https://github.com/pranjallk1995/Luna_Fiora/wiki/Getting-Started) | Setup, `.env`, sign-in, Gmail and Drive |
| [MCP tools](https://github.com/pranjallk1995/Luna_Fiora/wiki/MCP-Tools) | Every tool your assistant can call |
| [Architecture](https://github.com/pranjallk1995/Luna_Fiora/wiki/Architecture) | Services, privacy boundaries, model, data model and database diagram |
| [Development](https://github.com/pranjallk1995/Luna_Fiora/wiki/Development) | Development workflow and tests |
| [Operations](https://github.com/pranjallk1995/Luna_Fiora/wiki/Operations) | The database UI |

The UI follows [UI_STYLE_GUIDE.md](UI_STYLE_GUIDE.md).

## Releases and development

Releases are on the [Releases page](https://github.com/pranjallk1995/Luna_Fiora/releases). To update: `git pull`, then
`./Luna_Sentia/luna.sh start fiora`. To run your local code and reload it as you edit:
`./Luna_Sentia/luna.sh start --build --watch fiora`.
