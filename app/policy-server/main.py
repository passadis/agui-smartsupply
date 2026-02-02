from __future__ import annotations

import json
import os

import mcp.types as types
from azure.storage.blob import BlobServiceClient
from mcp.server import Server
from mcp.server.sse import SseServerTransport


mcp_server = Server("PolicyLibrarian")

BLOB_CONNECTION_STRING = os.getenv("BLOB_CONNECTION_STRING")
CONTAINER_NAME = os.getenv("POLICY_CONTAINER_NAME", "policies")


def _name_map(doc_name: str) -> str:
    clean = (doc_name or "").lower().strip()
    mapping = {
        "hazardous": "hazardous.txt",
        "electronics": "electronics.txt",
        "fragile": "fragile.txt",
    }
    return mapping.get(clean, doc_name)


def _blob_service_client() -> BlobServiceClient:
    if not BLOB_CONNECTION_STRING:
        raise ValueError("BLOB_CONNECTION_STRING environment variable is not set.")
    return BlobServiceClient.from_connection_string(BLOB_CONNECTION_STRING)


def _safe_storage_info(client: BlobServiceClient) -> dict:
    return {
        "account": getattr(client, "account_name", None),
        "container": CONTAINER_NAME,
    }


def _list_blobs(limit: int = 200) -> list[str]:
    client = _blob_service_client()
    container = client.get_container_client(CONTAINER_NAME)
    if not container.exists():
        return []

    names: list[str] = []
    for blob in container.list_blobs():
        names.append(blob.name)
        if len(names) >= limit:
            break
    return names


@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="read_policy_document",
            description=(
                "Retrieves the full content of a policy document from Azure Blob Storage. "
                "You can provide a filename (hazardous.txt/electronics.txt/fragile.txt) or a category (hazardous/electronics/fragile)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_name": {
                        "type": "string",
                        "enum": [
                            "hazardous.txt",
                            "electronics.txt",
                            "fragile.txt",
                            "hazardous",
                            "electronics",
                            "fragile",
                        ],
                        "description": "Policy filename or category name.",
                    }
                },
                "required": ["doc_name"],
            },
        ),
        types.Tool(
            name="list_policy_documents",
            description=(
                "Lists available policy blob names in the configured Azure Blob Storage container. "
                "Useful for debugging and tool selection."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@mcp_server.call_tool()
async def call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "list_policy_documents":
        try:
            client = _blob_service_client()
            storage = _safe_storage_info(client)
            available = _list_blobs(limit=200)
            return [
                types.TextContent(
                    type="text",
                    text=json.dumps({"storage": storage, "available": available}, ensure_ascii=False),
                )
            ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Error listing policies: {type(e).__name__}: {e}")]

    if name == "read_policy_document":
        requested = arguments.get("doc_name")
        if not requested:
            return [types.TextContent(type="text", text="Error: doc_name is required.")]

        doc_name = _name_map(requested)

        try:
            client = _blob_service_client()
            container = client.get_container_client(CONTAINER_NAME)
            if not container.exists():
                storage = _safe_storage_info(client)
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            "Policy container not found. "
                            + json.dumps({"storage": storage}, ensure_ascii=False)
                        ),
                    )
                ]

            blob_client = container.get_blob_client(doc_name)
            if not blob_client.exists():
                storage = _safe_storage_info(client)
                available = _list_blobs(limit=50)
                return [
                    types.TextContent(
                        type="text",
                        text=(
                            f"Document '{doc_name}' not found in policy library. "
                            + json.dumps({"storage": storage, "available": available}, ensure_ascii=False)
                        ),
                    )
                ]

            content = blob_client.download_blob().readall().decode("utf-8")
            return [types.TextContent(type="text", text=content)]

        except Exception as e:
            return [types.TextContent(type="text", text=f"Error accessing policy library: {type(e).__name__}: {e}")]

    raise ValueError(f"Unknown tool: {name}")

# SSE Transport
sse = SseServerTransport("/messages")


def _cors_headers() -> list[tuple[bytes, bytes]]:
    # Minimal permissive CORS for local dev / demos.
    # If you want to lock this down, replace '*' with your UI origin.
    return [
        (b"access-control-allow-origin", b"*"),
        (b"access-control-allow-methods", b"GET,POST,OPTIONS"),
        (b"access-control-allow-headers", b"content-type"),
    ]


async def _send_options(send):
    await send(
        {
            "type": "http.response.start",
            "status": 204,
            "headers": _cors_headers(),
        }
    )
    await send({"type": "http.response.body", "body": b""})

async def app(scope, receive, send):
    """
    Raw ASGI Application to handle SSE and POST requests without framework overhead.
    """
    if scope["type"] != "http":
        return

    async def send_with_cors(message):
        if message.get("type") == "http.response.start":
            headers = list(message.get("headers") or [])
            existing = {k.lower() for (k, _v) in headers}
            for k, v in _cors_headers():
                if k.lower() not in existing:
                    headers.append((k, v))
            message = {**message, "headers": headers}
        await send(message)

    if scope["path"] == "/sse" and scope["method"] == "GET":
        async with sse.connect_sse(scope, receive, send_with_cors) as streams:
            # Manually run the server with the transport streams
            await mcp_server.run(
                streams[0], 
                streams[1], 
                mcp_server.create_initialization_options()
            )
        return

    if scope["path"] == "/messages" and scope["method"] == "POST":
        await sse.handle_post_message(scope, receive, send_with_cors)
        return

    # 404 Response
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [(b"content-type", b"text/plain"), *_cors_headers()],
    })
    await send({
        "type": "http.response.body",
        "body": b"Not Found",
    })
