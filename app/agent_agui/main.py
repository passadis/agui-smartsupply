import asyncio
import json
import os
import uuid
from contextlib import AsyncExitStack
from contextlib import suppress
from contextvars import ContextVar
from collections.abc import Callable
from typing import Annotated, Any, AsyncIterator, Literal
import re

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from pydantic import BaseModel

from azure.identity import AzureCliCredential
from agent_framework.azure import AzureOpenAIChatClient

from mcp import ClientSession
from mcp.client.sse import sse_client


load_dotenv()


class AgUiRequest(BaseModel):
    threadId: str = "default-thread"
    message: str


class ApprovalResponse(BaseModel):
    approvalId: str
    approved: bool


EmitFn = Callable[[dict[str, Any]], None]
_emit_event: ContextVar[EmitFn | None] = ContextVar("_emit_event", default=None)


class McpBridge:
    def __init__(self) -> None:
        self._stack: AsyncExitStack | None = None
        self.policy_session: ClientSession | None = None
        self.order_session: ClientSession | None = None

    async def start(self) -> None:
        policy_url = os.getenv("POLICY_SERVER_URL", "http://localhost:8000/sse")
        order_url = os.getenv("ORDER_SERVER_URL", "http://localhost:8001/sse")

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        policy_transport = await self._stack.enter_async_context(sse_client(policy_url))
        self.policy_session = await self._stack.enter_async_context(
            ClientSession(policy_transport[0], policy_transport[1])
        )
        await self.policy_session.initialize()

        order_transport = await self._stack.enter_async_context(sse_client(order_url))
        self.order_session = await self._stack.enter_async_context(
            ClientSession(order_transport[0], order_transport[1])
        )
        await self.order_session.initialize()

    async def stop(self) -> None:
        if self._stack is not None:
            await self._stack.__aexit__(None, None, None)
            self._stack = None
        self.policy_session = None
        self.order_session = None

    async def call(self, tool_name: str, arguments: dict[str, Any]) -> str:
        if self.policy_session is None or self.order_session is None:
            raise RuntimeError("MCP bridge not initialized")

        if tool_name in {"read_policy_document", "list_policy_documents"}:
            session = self.policy_session
        else:
            session = self.order_session

        result = await session.call_tool(tool_name, arguments)

        if hasattr(result, "content") and result.content:
            parts: list[str] = []
            for content_item in result.content:
                if hasattr(content_item, "text"):
                    parts.append(content_item.text)
                else:
                    parts.append(str(content_item))
            return "".join(parts)

        return str(result)


mcp_bridge = McpBridge()


_approval_lock = asyncio.Lock()
_pending_approvals: dict[str, asyncio.Future[bool]] = {}


def _sse(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _emit_agui_event(queue: asyncio.Queue[dict[str, Any]], event: dict[str, Any]) -> None:
    queue.put_nowait(event)


def _get_agent():
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")

    if not endpoint or not deployment:
        raise RuntimeError(
            "Missing Azure OpenAI configuration. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_CHAT_DEPLOYMENT_NAME."
        )

    if api_key:
        client = AzureOpenAIChatClient(endpoint=endpoint, deployment_name=deployment, api_key=api_key)
    else:
        client = AzureOpenAIChatClient(
            credential=AzureCliCredential(), endpoint=endpoint, deployment_name=deployment
        )

    instructions = (
        "You are a helpful supply chain assistant. "
        "You can look up orders and read shipping policy documents. "
        "Use tools when needed, then answer clearly and briefly. "
        "Use list_policy_documents to discover which policy documents are available. "
        "\n\n"
        "Order address workflow: "
        "- When asked about an order status (e.g., 'order status 4444?'), call get_order_details and report Status and any Remarks/DeliveryAddress fields if present. "
        "- If an order is Delayed or Returned and Remarks mention a wrong address plus a corrected address, explain the issue and quote the corrected address from Remarks. "
        "- When instructed 'Fix order <id>' (or equivalent like 'Proceed to fix order <id>'), do NOT ask a follow-up yes/no question. "
        "  Instead: call fix_order_wrong_address(<id>) which will (a) extract corrected address from Remarks, (b) request human approval to update DeliveryAddress, "
        "  then (c) update Status to 'Processing' and (d) update Remarks to begin with 'RESOLVED:' so future operators are not confused."
    )

    return client.as_agent(
        name="SupplyChainAgent",
        instructions=instructions,
        tools=[
            list_policy_documents,
            read_policy_document,
            get_order_details,
            get_order_address,
            set_order_address,
            set_order_remarks,
            fix_order_wrong_address,
            get_order_photo,
            set_order_photo,
            update_order_status,
            list_orders_by_status,
        ],
    )


async def list_policy_documents() -> str:
    """List available policy documents from the Policy MCP server (Azure Blob-backed)."""
    result = await mcp_bridge.call("list_policy_documents", {})
    await _tool_event("list_policy_documents", {}, result)
    return result


async def _tool_event(tool_name: str, arguments: dict[str, Any], result: str) -> None:
    emit = _emit_event.get()
    if emit is None:
        return

    # Optional step boundaries for UIs that visualize run progress.
    step_name = f"tool:{tool_name}"
    emit({"type": "StepStarted", "stepName": step_name})

    tool_call_id = str(uuid.uuid4())

    emit({"type": "ToolCallStart", "toolCallId": tool_call_id, "toolCallName": tool_name})
    emit({"type": "ToolCallArgs", "toolCallId": tool_call_id, "delta": json.dumps(arguments)})
    emit({"type": "ToolCallEnd", "toolCallId": tool_call_id})
    emit(
        {
            "type": "ToolCallResult",
            "messageId": str(uuid.uuid4()),
            "toolCallId": tool_call_id,
            "role": "tool",
            "content": result,
        }
    )

    # Convenience: if a tool returns an image URL (or JSON containing one), emit an AG-UI Custom event
    # so clients can render it as a rich card.
    def _looks_like_image_url(value: str) -> bool:
        v = value.lower().split("?")[0].split("#")[0]
        if not (v.startswith("http://") or v.startswith("https://")):
            return False
        return v.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"))

    image_url: str | None = None
    if isinstance(result, str) and _looks_like_image_url(result.strip()):
        image_url = result.strip()
    else:
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                for k in ("imageUrl", "image_url", "url", "image"):
                    v = parsed.get(k)
                    if isinstance(v, str) and _looks_like_image_url(v.strip()):
                        image_url = v.strip()
                        break
        except Exception:
            pass

    if image_url:
        emit({"type": "Custom", "name": "image", "value": {"url": image_url, "alt": tool_name}})

    emit({"type": "StepFinished", "stepName": step_name})


PolicyDocName = Literal[
    "hazardous.txt",
    "electronics.txt",
    "fragile.txt",
    # Allow common shorthand; the policy server maps these to the correct file.
    "hazardous",
    "electronics",
    "fragile",
]


async def read_policy_document(
    doc_name: Annotated[
        PolicyDocName,
        Field(
            description=(
                "Policy document to retrieve. Prefer the .txt filename (hazardous.txt, electronics.txt, fragile.txt). "
                "You may also pass the shorthand category (hazardous/electronics/fragile)."
            )
        ),
    ]
) -> str:
    """Retrieve the full content of a policy document (matches the Policy server tool)."""
    result = await mcp_bridge.call("read_policy_document", {"doc_name": doc_name})
    await _tool_event("read_policy_document", {"doc_name": doc_name}, result)
    return result


async def get_order_details(order_id: str) -> str:
    """Get status/priority/category for a single order."""
    result = await mcp_bridge.call("get_order_details", {"order_id": order_id})
    await _tool_event("get_order_details", {"order_id": order_id}, result)
    return result


async def get_order_address(order_id: str) -> str:
    """Get an order's delivery address (and remarks, if available)."""
    result = await mcp_bridge.call("get_order_address", {"order_id": order_id})
    await _tool_event("get_order_address", {"order_id": order_id}, result)
    return result


async def set_order_remarks(order_id: str, remarks: str) -> str:
    """Set order remarks (stored as Orders.Remarks)."""
    args: dict[str, Any] = {"order_id": order_id, "remarks": remarks}
    result = await mcp_bridge.call("set_order_remarks", args)
    await _tool_event("set_order_remarks", args, result)
    return result


async def get_order_photo(order_id: str) -> str:
    """Get an order photo URL (if present in the backing SQL schema)."""
    result = await mcp_bridge.call("get_order_photo", {"order_id": order_id})
    await _tool_event("get_order_photo", {"order_id": order_id}, result)
    return result


async def set_order_photo(order_id: str, photo_url: str) -> str:
    """Set an order photo URL (stored as Orders.OrderPhotoUrl)."""
    args: dict[str, Any] = {"order_id": order_id, "photo_url": photo_url}

    approved = await _request_approval(
        title="Confirm order photo update",
        description=f"You are about to set the photo URL for order {order_id}.",
        tool_name="set_order_photo",
        arguments=args,
        preview_image_url=photo_url,
    )

    if not approved:
        return json.dumps({"cancelled": True, "reason": "User rejected set_order_photo"})

    result = await mcp_bridge.call("set_order_photo", args)
    await _tool_event("set_order_photo", args, result)
    return result


async def set_order_address(order_id: str, delivery_address: str) -> str:
    """Set an order delivery address (stored as Orders.DeliveryAddress)."""
    args: dict[str, Any] = {"order_id": order_id, "delivery_address": delivery_address}

    approved = await _request_approval(
        title="Confirm delivery address update",
        description=(
            f"You are about to update the delivery address for order {order_id}. "
            "Please verify the address is correct before approving."
        ),
        tool_name="set_order_address",
        arguments=args,
        preview_image_url=None,
    )

    if not approved:
        return json.dumps({"cancelled": True, "reason": "User rejected set_order_address"})

    result = await mcp_bridge.call("set_order_address", args)
    await _tool_event("set_order_address", args, result)
    return result


def _extract_corrected_address_from_remarks(remarks: str) -> str | None:
    if not remarks or not isinstance(remarks, str):
        return None

    # Strip common markdown emphasis so we store a clean address.
    cleaned = remarks.replace("**", "").strip()

    # Prefer explicit patterns like: "correct address is ..." or "correct address: ..."
    patterns = [
        r"correct\s+address\s+is\s*[:\-]?\s*(.+)",
        r"correct\s+address\s*[:\-]\s*(.+)",
    ]
    for pat in patterns:
        m = re.search(pat, cleaned, flags=re.IGNORECASE)
        if not m:
            continue
        candidate = m.group(1).strip()
        # Stop at likely sentence boundaries or boilerplate.
        for stop in ("\n", "\r", "Proceed", "Shall I", "If you would like"):
            idx = candidate.lower().find(stop.lower())
            if idx != -1:
                candidate = candidate[:idx].strip()
        candidate = candidate.strip(" .\t")
        if candidate:
            return candidate

    return None


async def fix_order_wrong_address(order_id: str) -> str:
    """Fix an order when remarks indicate a wrong address.

    Flow:
    - Read order details (including remarks)
    - Extract corrected address from remarks
    - Ask approval to update DeliveryAddress (via set_order_address)
    - If approved: update status to Processing and mark remarks as RESOLVED
    """
    details_raw = await get_order_details(order_id)
    try:
        details = json.loads(details_raw)
    except Exception:
        return json.dumps({"error": "Could not parse order details", "details": details_raw})

    if isinstance(details, dict) and details.get("error"):
        return details_raw

    if not isinstance(details, dict):
        return json.dumps({"error": "Unexpected order details payload", "details": details})

    status = details.get("Status")
    remarks = details.get("Remarks")
    current_address = details.get("DeliveryAddress")

    corrected = _extract_corrected_address_from_remarks(str(remarks or ""))
    if not corrected:
        return json.dumps(
            {
                "order_id": order_id,
                "status": status,
                "deliveryAddress": current_address,
                "remarks": remarks,
                "message": "No corrected address found in remarks. Add a 'correct address is ...' line to Remarks and try again.",
            }
        )

    # Approval-gated address update.
    addr_result_raw = await set_order_address(order_id, corrected)
    try:
        addr_result = json.loads(addr_result_raw)
    except Exception:
        addr_result = None

    if isinstance(addr_result, dict) and addr_result.get("cancelled"):
        return addr_result_raw

    # Status update does not require approval.
    await update_order_status(order_id, new_status="Processing")

    # Make remarks unambiguous for future operators.
    resolved = (
        f"RESOLVED: Wrong address corrected. DeliveryAddress updated to: {corrected}. "
        "Status set to Processing.\n\n"
        "Previous remarks (for audit):\n"
        f"{(remarks or '').strip()}"
    ).strip()
    await set_order_remarks(order_id, resolved)

    return json.dumps(
        {
            "order_id": order_id,
            "previousStatus": status,
            "newStatus": "Processing",
            "updatedDeliveryAddress": corrected,
            "remarksUpdated": True,
        }
    )


async def _request_approval(
    *,
    title: str,
    description: str,
    tool_name: str,
    arguments: dict[str, Any],
    preview_image_url: str | None = None,
    timeout_s: float = 300.0,
) -> bool:
    emit = _emit_event.get()

    # If we're not in an AG-UI streaming context, default to "approved" so non-UI callers don't hang.
    if emit is None:
        return True

    approval_id = str(uuid.uuid4())
    loop = asyncio.get_running_loop()
    fut: asyncio.Future[bool] = loop.create_future()

    async with _approval_lock:
        _pending_approvals[approval_id] = fut

    step_name = f"approval:{tool_name}"
    emit({"type": "StepStarted", "stepName": step_name})
    emit(
        {
            "type": "Custom",
            "name": "approval_request",
            "value": {
                "approvalId": approval_id,
                "title": title,
                "description": description,
                "toolName": tool_name,
                "arguments": arguments,
                "previewImageUrl": preview_image_url,
            },
        }
    )

    approved = False
    try:
        approved = await asyncio.wait_for(fut, timeout=timeout_s)
    except asyncio.TimeoutError:
        emit(
            {
                "type": "Custom",
                "name": "approval_result",
                "value": {"approvalId": approval_id, "approved": False, "reason": "timeout"},
            }
        )
        approved = False
    finally:
        async with _approval_lock:
            _pending_approvals.pop(approval_id, None)

    emit({"type": "Custom", "name": "approval_result", "value": {"approvalId": approval_id, "approved": approved}})
    emit({"type": "StepFinished", "stepName": step_name})
    return approved


async def update_order_status(order_id: str, new_status: str | None = None, new_priority: str | None = None) -> str:
    """Update order status and/or priority."""
    args: dict[str, Any] = {"order_id": order_id}
    if new_status is not None:
        args["new_status"] = new_status
    if new_priority is not None:
        args["new_priority"] = new_priority

    result = await mcp_bridge.call("update_order_status", args)
    await _tool_event("update_order_status", args, result)
    return result


async def list_orders_by_status(status: str) -> str:
    """List all orders that match a given status."""
    result = await mcp_bridge.call("list_orders_by_status", {"status": status})
    await _tool_event("list_orders_by_status", {"status": status}, result)
    return result


app = FastAPI(title="agent_agui", version="0.1.0")

# Serve a lightweight modern web UI (no Streamlit/Next.js required)
_WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
app.mount("/static", StaticFiles(directory=_WEB_DIR), name="static")


@app.on_event("startup")
async def _startup() -> None:
    await mcp_bridge.start()


@app.on_event("shutdown")
async def _shutdown() -> None:
    await mcp_bridge.stop()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(os.path.join(_WEB_DIR, "index.html"))


@app.post("/agui/approval")
async def agui_approval(resp: ApprovalResponse) -> dict[str, Any]:
    async with _approval_lock:
        fut = _pending_approvals.get(resp.approvalId)

    if fut is None:
        return {"ok": False, "error": "Unknown approvalId"}

    if not fut.done():
        fut.set_result(bool(resp.approved))

    return {"ok": True}


@app.post("/agui")
async def agui_stream(req: AgUiRequest):
    agent = _get_agent()

    thread_id = req.threadId or "default-thread"
    run_id = str(uuid.uuid4())
    message_id = str(uuid.uuid4())

    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def emit(event: dict[str, Any]) -> None:
        _emit_agui_event(queue, event)

    async def event_generator() -> AsyncIterator[str]:
        token = _emit_event.set(emit)
        done = asyncio.Event()

        async def run_agent() -> None:
            try:
                emit({"type": "RunStarted", "threadId": thread_id, "runId": run_id, "input": {"message": req.message}})
                emit({"type": "TextMessageStart", "messageId": message_id, "role": "assistant"})

                async for chunk in agent.run_stream(req.message):
                    if getattr(chunk, "text", None):
                        emit({"type": "TextMessageContent", "messageId": message_id, "delta": chunk.text})

                emit({"type": "TextMessageEnd", "messageId": message_id})
                emit({"type": "RunFinished", "threadId": thread_id, "runId": run_id})
            except Exception as e:
                emit({"type": "RunError", "message": f"{type(e).__name__}: {e}"})
            finally:
                done.set()

        task = asyncio.create_task(run_agent())
        last_keepalive = asyncio.get_running_loop().time()

        try:
            while not done.is_set() or not queue.empty():
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=0.5)
                    yield _sse(evt)
                except asyncio.TimeoutError:
                    now = asyncio.get_running_loop().time()
                    if now - last_keepalive >= 10.0:
                        # SSE comment keepalive (ignored by our parser, but keeps proxies happy)
                        yield ": keepalive\n\n"
                        last_keepalive = now
        finally:
            task.cancel()
            with suppress(Exception):
                await task
            _emit_event.reset(token)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
        },
    )
