import streamlit as st
import asyncio
import os
import json
import time
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from openai import AsyncAzureOpenAI
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# Load environment variables
load_dotenv()

# --- Configuration ---
# In a real workshop, these would be pulled from os.environ
POLICY_SERVER_URL = os.getenv("POLICY_SERVER_URL", "http://localhost:8000/sse")
ORDER_SERVER_URL = os.getenv("ORDER_SERVER_URL", "http://localhost:8001/sse")

AOAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AOAI_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AOAI_DEPLOYMENT = "gpt4o" # Your deployment name

st.set_page_config(page_title="Supply Chain AI Agent", layout="wide", page_icon="📦")

# --- UI & Styling ---
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        background: -webkit-linear-gradient(45deg, #FF6B6B, #4ECDC4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }
    .stChatInput {
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/4565/4565578.png", width=120) # Placeholder Logo
    st.markdown("### 🌐 Supply Chain Command")
    st.caption("Connected to Azure MCP Fabric")
    with st.expander("System Status"):
        st.success("User Interface: Online")
        st.info("Policy Server: Standby")
        st.info("Order Server: Standby")

st.markdown('<div class="main-header">📦 Supply Chain Command Center</div>', unsafe_allow_html=True)
st.caption("AI-Powered Logistics & Compliance Assistant")
st.divider()

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Controls
# with st.sidebar:
#     st.header("Actions")
#     if st.button("💾 End Session & Save Log"):
#         pass # Disabled for debugging

# Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

async def run_chat_loop(user_input):
    """
    The Main Async Loop:
    1. Connects to BOTH MCP Servers.
    2. Aggregates tools.
    3. Manages the conversation with Azure OpenAI.
    """
    
    # Initialize Azure OpenAI Client
    # Ensure variables are set
    if not AOAI_ENDPOINT or not AOAI_KEY:
        st.error("Azure OpenAI Endpoint or Key is missing. Please check your environment variables (.env).")
        return

    aclient = AsyncAzureOpenAI(
        azure_endpoint=AOAI_ENDPOINT,
        api_key=AOAI_KEY,
        api_version="2024-12-01-preview"
    )

    # Use AsyncExitStack to manage multiple server connections
    try:
        async with AsyncExitStack() as stack:
            # Create a status container for the connection phase
            with st.status("🔗 Establishing MCP Uplink...", expanded=True) as status:
                # --- Connect to Policy Server ---
                st.write("🔹 Connecting to Policy Server...")
                policy_transport = await stack.enter_async_context(sse_client(POLICY_SERVER_URL))
                policy_session = await stack.enter_async_context(ClientSession(policy_transport[0], policy_transport[1]))
                await policy_session.initialize()
                
                # --- Connect to Order Server ---
                st.write("🔹 Connecting to Order Server...")
                order_transport = await stack.enter_async_context(sse_client(ORDER_SERVER_URL))
                order_session = await stack.enter_async_context(ClientSession(order_transport[0], order_transport[1]))
                await order_session.initialize()

                status.update(label="✅ System Online & Connected", state="complete", expanded=False)
            
            # --- Aggregation Strategy ---
            # 1. Fetch tools from both servers
            policy_tools = await policy_session.list_tools()
            order_tools = await order_session.list_tools()
            
            # 2. Build a Master Tool List for OpenAI
            all_tools_definitions = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}}
                for t in policy_tools.tools + order_tools.tools
            ]

            # 3. Build a Routing Map to know which session to call
            # { "get_handling_policy": policy_session, "get_order_details": order_session }
            tool_router = {}
            for t in policy_tools.tools: tool_router[t.name] = policy_session
            for t in order_tools.tools: tool_router[t.name] = order_session

            # --- The Conversation Loop ---
            # Messages are already in session_state, just prepare them for API
            messages = [
                {"role": "system", "content": "You are a helpful supply chain assistant. You have access to order data and shipping policies. Use them to answer user questions."}
            ] + st.session_state.messages

            with st.chat_message("assistant"):
                # First Call to LLM
                response = await aclient.chat.completions.create(
                    model=AOAI_DEPLOYMENT,
                    messages=messages,
                    tools=all_tools_definitions,
                    tool_choice="auto",
                )

                response_message = response.choices[0].message

                # Tool-calling branch
                if response_message.tool_calls:
                    # Append assistant tool-call request to messages
                    messages.append(response_message)

                    for tool_call in response_message.tool_calls:
                        function_name = tool_call.function.name
                        arguments = json.loads(tool_call.function.arguments)

                        with st.status(f"🛠️ Executing: {function_name}", expanded=False):
                            st.json(arguments)

                            session = tool_router.get(function_name)
                            if not session:
                                messages.append(
                                    {
                                        "tool_call_id": tool_call.id,
                                        "role": "tool",
                                        "name": function_name,
                                        "content": "Error: Tool execution failed. Session not found.",
                                    }
                                )
                                continue

                            result = await session.call_tool(function_name, arguments)

                            # Convert result content to string
                            content_str = ""
                            if hasattr(result, "content"):
                                for c in result.content:
                                    if hasattr(c, "text"):
                                        content_str += c.text
                                    else:
                                        content_str += str(c)
                            else:
                                content_str = str(result)

                            messages.append(
                                {
                                    "tool_call_id": tool_call.id,
                                    "role": "tool",
                                    "name": function_name,
                                    "content": content_str,
                                }
                            )

                    # Follow-up call to LLM with tool outputs
                    final_response = await aclient.chat.completions.create(
                        model=AOAI_DEPLOYMENT,
                        messages=messages,
                    )
                    final_content = final_response.choices[0].message.content or ""
                    st.markdown(final_content)
                    st.session_state.messages.append({"role": "assistant", "content": final_content})

                # Non-tool branch
                else:
                    final_content = response_message.content or ""
                    st.markdown(final_content)
                    st.session_state.messages.append({"role": "assistant", "content": final_content})

    except Exception as e:
        st.error(f"An error occurred: {type(e).__name__}: {e}")
        import traceback
        st.code(traceback.format_exc())


# Chat input (must be at top-level so it always renders)
if prompt := st.chat_input("How can I help you?"):
    # Show the user's message immediately
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    asyncio.run(run_chat_loop(prompt))
                        
