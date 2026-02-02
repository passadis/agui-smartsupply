<p align="center">
  <a href="https://skillicons.dev">
    <img src="https://skillicons.dev/icons?i=python,fastapi,docker,ai,azure" />
  </a>
</p>

<h1 align="center">MCP & AG‑UI: A Python-first multi-tool agent demo with Microsoft Agents SDK (Azure OpenAI)</h1>


This repo is a complete, Python-first demo that connects:

- **Two MCP servers** (Policy + Orders) exposed over **SSE + JSON-RPC**
- A **Microsoft Agent Framework** (Agents SDK) agent backed by **Azure OpenAI**
- A modern, lightweight **AG‑UI** web app (served by FastAPI) that renders:
  - streaming assistant text
  - tool calls (args/results)
  - **images** (order photos)
  - **human approval** cards for state-changing actions

It’s designed as a practical pattern you can reuse: keep backends as MCP tools, keep the “agent brain” in one service, and give users a UI that makes tool activity visible and trustworthy.

<img width="3328" height="1280" alt="Gemini_Generated_Image_imoleimoleimolei" src="https://github.com/user-attachments/assets/273611a7-bedc-4bf2-89e4-0dfc1a4f2dc0" />

## What’s inside

### 1) Policy MCP server (Blob-only)
- Location: [app/policy-server/main.py](app/policy-server/main.py)
- Transport:
  - `GET /sse` for server-sent events
  - `POST /messages?session_id=...` for JSON-RPC messages
- Tools:
  - `list_policy_documents` — lists policy blobs available in a container
  - `read_policy_document` — fetches a policy document from Azure Blob Storage

**Important:** policies are **Blob Storage as the source of truth** (no local file fallback).

### 2) Order MCP server (Azure SQL)
- Location: [app/order-server/main.py](app/order-server/main.py)
- Tools:
  - `get_order_details`
  - `list_orders_by_status`
  - `update_order_status`
  - `get_order_photo` — returns JSON with `imageUrl`
  - `set_order_photo` — writes `OrderPhotoUrl` (optionally gated by UI approval in the agent service)

Schema helper:
- [setup.sql](setup.sql) creates the `Orders` table, including `OrderPhotoUrl`.

### 3) Agent + AG‑UI service (FastAPI)
- Location: [app/agent_agui/main.py](app/agent_agui/main.py)
- Responsibilities:
  - Connects to both MCP servers via SSE
  - Creates an Azure OpenAI agent using Microsoft Agent Framework
  - Streams **AG‑UI events** over SSE from `POST /agui`
  - Serves a modern UI from `GET /`
  - Adds an interactive **approval** endpoint `POST /agui/approval`

This service enriches the experience by emitting AG‑UI events such as:
- lifecycle: `RunStarted`, `RunFinished`, `RunError`
- streaming text: `TextMessageStart/Content/End`
- tool tracing: `ToolCallStart/Args/End/Result`
- progress: `StepStarted/StepFinished`
- rich UI: `Custom:image` and `Custom:approval_request`

### 4) Web UI (no Streamlit/Next.js required)
- Location: [app/agent_agui/web/index.html](app/agent_agui/web/index.html), [app/agent_agui/web/app.js](app/agent_agui/web/app.js), [app/agent_agui/web/styles.css](app/agent_agui/web/styles.css)

It’s intentionally “boring-tech”: just HTML/CSS/JS. The UI parses the SSE stream and renders:
- a chat transcript
- a tools panel
- a raw event feed
- **image cards** when the agent emits `Custom:image`
- a glossy **Approve/Reject** card for `set_order_photo`

## Why this pattern works

- **Clean boundaries:** MCP servers stay focused on domain logic (policy retrieval, orders/SQL).
- **Tool transparency:** AG‑UI makes tool calls visible, not hidden.
- **Trust & safety:** state-changing actions can be gated behind human approval.
- **Extensible UX:** “tool returns imageUrl → UI shows image” is a great example of tool-shaped rendering.

## Quickstart (Docker)

### Prereqs
- Docker Desktop
- Azure resources:
  - Azure OpenAI: endpoint + chat deployment
  - Azure SQL: reachable connection string
  - Azure Blob Storage: container with policy docs

### Configure environment
Copy and edit your env file:

- Create `.env` (or edit existing) based on `.env.sample`

Common variables:
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- `AZURE_OPENAI_API_KEY` (or use `az login` locally when not in Docker)
- `SQL_CONNECTION_STRING`
- `POLICY_CONTAINER_NAME` (defaults to `policies`)

### Start everything
From repo root:

- `docker compose up --build -d`

Services (default ports):
- Policy MCP server: `http://localhost:8000/sse`
- Order MCP server: `http://localhost:8001/sse`
- Agent + AG‑UI UI: `http://localhost:9000/`
- Streamlit sample (optional): `http://localhost:8501/`

## Demo script (what to try)

1) **Show an order photo (image rendering)**
- Ask in the UI: “Show me the photo for order 5390”
- Expected:
  - tool call `get_order_photo`
  - `Custom:image` event
  - image card rendered

2) **Attempt to set a photo (approval gating)**
- Ask: “Set the photo for order 5390 to https://…/order_5390.jpg”
- Expected:
  - approval card appears
  - click **Approve** → `set_order_photo` executes
  - click **Reject** → action is cancelled

3) **Policy lookup**
- Ask: “List available policy docs, then read the hazardous policy.”

## Notes on the data model

Orders include a nullable `OrderPhotoUrl` field (a URL). This is a pragmatic demo choice:
- It keeps SQL as the “index” and Blob as the “payload”.
- The UI can render the image directly once the URL is returned.

If you want to be stricter in production:
- store only a blob name/key in SQL
- generate short-lived SAS URLs in a dedicated service

## How the pieces talk

- The MCP servers implement SSE transport:
  - Client opens `GET /sse`
  - Server emits an `endpoint` SSE event telling the client where to POST JSON-RPC messages
- The agent service uses an MCP client over SSE to call tools.
- The agent service streams AG‑UI events to the browser via `POST /agui`.
- The browser renders events live and can respond (approval) via `POST /agui/approval`.

## Troubleshooting

- If tools can’t reach Azure SQL, verify `SQL_CONNECTION_STRING` and network/firewall rules.
- If policy docs aren’t found, check `POLICY_CONTAINER_NAME` and that your Blob container has the expected blobs.
- If images don’t render, confirm the URL ends with a common extension like `.jpg`/`.png` and is publicly accessible (or your browser can access it).

## Credits / tech stack

- Microsoft Agent Framework (Python Agents SDK)
- Azure OpenAI
- MCP (Model Context Protocol)
- FastAPI + SSE
- Plain HTML/CSS/JS UI

---



