# AG-UI Agent Service (Python)

A Python-first agent runtime that:
- Uses **Microsoft Agent Framework** with **Azure OpenAI**
- Calls the existing MCP servers (policy + order) as tools
- Streams **AG-UI events** over **SSE**

## Environment

Azure OpenAI (Agent Framework):
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_CHAT_DEPLOYMENT_NAME`
- Auth: either `AZURE_OPENAI_API_KEY` or `az login`

MCP server endpoints:
- `POLICY_SERVER_URL` (default: `http://localhost:8000/sse`)
- `ORDER_SERVER_URL` (default: `http://localhost:8001/sse`)

## Run locally

From repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r src/agent_agui/requirements.txt

uvicorn main:app --app-dir src/agent_agui --host 0.0.0.0 --port 9000
```

Health check:
- `GET http://localhost:9000/health`

Web UI:
- `GET http://localhost:9000/`

UI features:
- Streams AG-UI lifecycle + tool call events.
- Shows tool arguments/results in a side panel.
- Renders images when the stream emits `Custom` events with `name: "image"`.

Image rendering tip:
- If a tool result is JSON that contains an `imageUrl` (or `url`) pointing to a common image type (png/jpg/webp/gif/svg), the server auto-emits `Custom:image` so the UI shows an image card.

AG-UI SSE endpoint:
- `POST http://localhost:9000/agui`

Example request body:
```json
{
  "threadId": "demo-thread",
  "message": "Order 9921 is stuck. Check the order and relevant policy." 
}
```

The response is an SSE stream where each `data:` line is a JSON AG-UI event.
