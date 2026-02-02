from mcp.server import Server
from mcp.server.sse import SseServerTransport
import mcp.types as types
import os
import pyodbc
import json

# Initialize MCP Server
mcp_server = Server("SQLOrderAgent")

# SQL Configuration
SQL_CONNECTION_STRING = os.getenv("SQL_CONNECTION_STRING")

def get_db_connection():
    if not SQL_CONNECTION_STRING:
        raise ValueError("SQL_CONNECTION_STRING environment variable is not set.")
    return pyodbc.connect(SQL_CONNECTION_STRING)

def dict_from_row(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def _column_exists(conn: pyodbc.Connection, table_name: str, column_name: str) -> bool:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
        """,
        (table_name, column_name),
    )
    return cursor.fetchone() is not None

@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_order_details",
            description="Queries the SQL database for order details (status, priority, category, and optional fields like photo/address/remarks if present).",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="get_order_address",
            description="Returns an order's delivery address (and remarks if available) from the SQL database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."}
                },
                "required": ["order_id"]
            },
        ),
        types.Tool(
            name="set_order_address",
            description="Sets/replaces the order delivery address (stored in Orders.DeliveryAddress).",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."},
                    "delivery_address": {"type": "string", "description": "The delivery address for the order."}
                },
                "required": ["order_id", "delivery_address"]
            },
        ),
        types.Tool(
            name="set_order_remarks",
            description="Sets/replaces the order remarks (stored in Orders.Remarks). Use this to mark issues as RESOLVED after actions are taken.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."},
                    "remarks": {"type": "string", "description": "The full remarks text to store for the order."}
                },
                "required": ["order_id", "remarks"]
            },
        ),
        types.Tool(
            name="get_order_photo",
            description="Returns an order photo URL when available. Produces JSON with an imageUrl field.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="set_order_photo",
            description="Sets/replaces the order photo URL (stored in Orders.OrderPhotoUrl).",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."},
                    "photo_url": {"type": "string", "description": "A URL to an image for the order."}
                },
                "required": ["order_id", "photo_url"]
            }
        ),
        types.Tool(
            name="update_order_status",
            description="Updates the status or priority of an order in the SQL database.",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "The ID of the order."},
                    "new_status": {"type": "string", "description": "The new status (optional)."},
                    "new_priority": {"type": "string", "description": "The new priority (optional)."}
                },
                "required": ["order_id"]
            }
        ),
        types.Tool(
            name="list_orders_by_status",
            description="Retrieves a list of orders filtered by their status (e.g., 'Delayed', 'Processing', 'Shipped'). Returns multiple orders.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "The status to filter by (e.g., 'Delayed')."}
                },
                "required": ["status"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name == "get_order_details":
        order_id = arguments.get("order_id")
        try:
            with get_db_connection() as conn:
                has_photo = _column_exists(conn, "Orders", "OrderPhotoUrl")
                has_address = _column_exists(conn, "Orders", "DeliveryAddress")
                has_remarks = _column_exists(conn, "Orders", "Remarks")
                cursor = conn.cursor()

                select_cols = ["OrderID", "Status", "Priority", "Category"]
                if has_photo:
                    select_cols.append("OrderPhotoUrl")
                if has_address:
                    select_cols.append("DeliveryAddress")
                if has_remarks:
                    select_cols.append("Remarks")

                cursor.execute(
                    f"SELECT {', '.join(select_cols)} FROM Orders WHERE OrderID = ?",
                    (order_id,),
                )
                
                rows = dict_from_row(cursor)
                if rows:
                    return [types.TextContent(type="text", text=json.dumps(rows[0]))]
                else:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "get_order_address":
        order_id = arguments.get("order_id")
        try:
            with get_db_connection() as conn:
                if not _column_exists(conn, "Orders", "DeliveryAddress"):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "DeliveryAddress column not found",
                                    "hint": "Update your Orders table to include DeliveryAddress (see setup.sql)",
                                }
                            ),
                        )
                    ]

                has_remarks = _column_exists(conn, "Orders", "Remarks")
                cursor = conn.cursor()
                if has_remarks:
                    cursor.execute(
                        "SELECT OrderID, DeliveryAddress, Remarks FROM Orders WHERE OrderID = ?",
                        (order_id,),
                    )
                else:
                    cursor.execute(
                        "SELECT OrderID, DeliveryAddress FROM Orders WHERE OrderID = ?",
                        (order_id,),
                    )

                rows = dict_from_row(cursor)
                if not rows:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]

                payload: dict[str, object] = {
                    "order_id": order_id,
                    "deliveryAddress": rows[0].get("DeliveryAddress"),
                }
                if has_remarks:
                    payload["remarks"] = rows[0].get("Remarks")
                return [types.TextContent(type="text", text=json.dumps(payload))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "set_order_address":
        order_id = arguments.get("order_id")
        delivery_address = arguments.get("delivery_address")

        try:
            with get_db_connection() as conn:
                if not _column_exists(conn, "Orders", "DeliveryAddress"):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "DeliveryAddress column not found",
                                    "hint": "Update your Orders table to include DeliveryAddress (see setup.sql)",
                                }
                            ),
                        )
                    ]

                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE Orders SET DeliveryAddress = ? WHERE OrderID = ?",
                    (delivery_address, order_id),
                )
                conn.commit()

                if cursor.rowcount <= 0:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"order_id": order_id, "deliveryAddress": delivery_address}),
                    )
                ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "set_order_remarks":
        order_id = arguments.get("order_id")
        remarks = arguments.get("remarks")

        try:
            with get_db_connection() as conn:
                if not _column_exists(conn, "Orders", "Remarks"):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "Remarks column not found",
                                    "hint": "Update your Orders table to include Remarks (see setup.sql)",
                                }
                            ),
                        )
                    ]

                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE Orders SET Remarks = ? WHERE OrderID = ?",
                    (remarks, order_id),
                )
                conn.commit()

                if cursor.rowcount <= 0:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"order_id": order_id, "remarks": remarks}),
                    )
                ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "get_order_photo":
        order_id = arguments.get("order_id")
        try:
            with get_db_connection() as conn:
                if not _column_exists(conn, "Orders", "OrderPhotoUrl"):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "OrderPhotoUrl column not found",
                                    "hint": "Update your Orders table to include OrderPhotoUrl (see setup.sql)",
                                }
                            ),
                        )
                    ]

                cursor = conn.cursor()
                cursor.execute(
                    "SELECT OrderID, OrderPhotoUrl FROM Orders WHERE OrderID = ?",
                    (order_id,),
                )
                rows = dict_from_row(cursor)
                if not rows:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]

                photo_url = rows[0].get("OrderPhotoUrl")
                payload = {"order_id": order_id, "imageUrl": photo_url}
                if not photo_url:
                    payload["message"] = "No photo is set for this order"
                return [types.TextContent(type="text", text=json.dumps(payload))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "set_order_photo":
        order_id = arguments.get("order_id")
        photo_url = arguments.get("photo_url")
        try:
            with get_db_connection() as conn:
                if not _column_exists(conn, "Orders", "OrderPhotoUrl"):
                    return [
                        types.TextContent(
                            type="text",
                            text=json.dumps(
                                {
                                    "error": "OrderPhotoUrl column not found",
                                    "hint": "Update your Orders table to include OrderPhotoUrl (see setup.sql)",
                                }
                            ),
                        )
                    ]

                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE Orders SET OrderPhotoUrl = ? WHERE OrderID = ?",
                    (photo_url, order_id),
                )
                conn.commit()

                if cursor.rowcount <= 0:
                    return [types.TextContent(type="text", text=json.dumps({"error": "Order not found"}))]

                return [
                    types.TextContent(
                        type="text",
                        text=json.dumps({"order_id": order_id, "imageUrl": photo_url}),
                    )
                ]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "list_orders_by_status":
        status = arguments.get("status")
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT OrderID, Status, Priority, Category FROM Orders WHERE Status = ?", (status,))
                
                rows = dict_from_row(cursor)
                if rows:
                    return [types.TextContent(type="text", text=json.dumps(rows))]
                else:
                    return [types.TextContent(type="text", text=json.dumps({"message": f"No orders found with status '{status}'"}))]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

    elif name == "update_order_status":
        order_id = arguments.get("order_id")
        new_status = arguments.get("new_status")
        new_priority = arguments.get("new_priority")
        
        updates = []
        params = []
        
        if new_status:
            updates.append("Status = ?")
            params.append(new_status)
        if new_priority:
            updates.append("Priority = ?")
            params.append(new_priority)
            
        if not updates:
            return [types.TextContent(type="text", text="No updates specified.")]
        
        # Add ID to params
        params.append(order_id)
        
        sql = f"UPDATE Orders SET {', '.join(updates)} WHERE OrderID = ?"
        
        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                row_count = cursor.rowcount
                if row_count > 0:
                    return [types.TextContent(type="text", text=f"Order {order_id} updated successfully.")]
                else:
                    return [types.TextContent(type="text", text="Order not found or no changes made.")]
        except Exception as e:
            return [types.TextContent(type="text", text=f"Database error: {str(e)}")]

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

    # CORS preflight
    if scope["method"] == "OPTIONS" and scope["path"] in ("/sse", "/messages"):
        await _send_options(send)
        return

    if scope["path"] == "/sse" and scope["method"] == "GET":
        async with sse.connect_sse(scope, receive, send_with_cors) as streams:
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
