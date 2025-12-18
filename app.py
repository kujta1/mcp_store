import streamlit as st
from groq import Groq
import httpx
import json
import os
from dotenv import load_dotenv
load_dotenv()
# --- 1. CONFIGURATION ---
# ST_TITLE = "🖥️ TechSupport AI Andela"
ST_TITLE = " TechSupport AI Andela"

MCP_URL = "https://vipfapwm3x.us-east-1.awsapprunner.com/mcp"
GROQ_MODEL = "llama-3.3-70b-versatile"

# --- 2. MCP TOOL DEFINITIONS ---
# We map the tools we discovered to Groq's function schema
TOOLS = [
    # 1. Browse & Search
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List computer products by category (e.g., 'Computers', 'Monitors', 'Printers').",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Find products using keywords (e.g., 'gaming laptop' or 'wireless mouse').",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product",
            "description": "Get pricing, inventory, and detailed specs for a specific product SKU.",
            "parameters": {
                "type": "object",
                "properties": {"sku": {"type": "string"}},
                "required": ["sku"]
            }
        }
    },
    # 2. Customer & Security
    {
        "type": "function",
        "function": {
            "name": "get_customer",
            "description": "Look up customer details (name, address) using their UUID.",
            "parameters": {
                "type": "object",
                "properties": {"customer_id": {"type": "string"}},
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "verify_customer_pin",
            "description": "Authenticate a customer using their email and 4-digit PIN. Essential before placing orders.",
            "parameters": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "pin": {"type": "string"}
                },
                "required": ["email", "pin"]
            }
        }
    },
    # 3. Orders & Tracking
    {
        "type": "function",
        "function": {
            "name": "list_orders",
            "description": "View order history for a customer. Can filter by status (fulfilled, pending, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "status": {"type": "string"}
                },
                "required": ["customer_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_order",
            "description": "Get detailed status and line items for a specific Order ID.",
            "parameters": {
                "type": "object",
                "properties": {"order_id": {"type": "string"}},
                "required": ["order_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Place a new order for a verified customer with specific SKUs and quantities.",
            "parameters": {
                "type": "object",
                "properties": {
                    "customer_id": {"type": "string"},
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "sku": {"type": "string"},
                                "quantity": {"type": "integer"}
                            }
                        }
                    }
                },
                "required": ["customer_id", "items"]
            }
        }
    }
]
# --- 3. HELPER FUNCTIONS ---


def call_mcp_server(name, args):
    """Bridge to the MCP server with the required strict headers."""
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {"name": name, "arguments": args}
    }
    try:
        response = httpx.post(MCP_URL, json=payload,
                              headers=headers, timeout=20.0)
        result = response.json()
        # MCP usually returns a list of content items
        content_list = result.get("result", {}).get("content", [])
        return "\n".join([c.get("text", "") for c in content_list])
    except Exception as e:
        return f"Error calling tool: {str(e)}"


# --- 4. STREAMLIT UI ---
st.set_page_config(page_title="MCP Chatbot", page_icon="🤖")
st.title(ST_TITLE)

# Securely get API Key from environment or sidebar
api_key = os.getenv("GROQ_API_KEY") or st.sidebar.text_input(
    "Enter Groq API Key", type="password")

if not api_key:
    st.info("Please provide a Groq API Key to start.")
    st.stop()

client = Groq(api_key=api_key)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
# for message in st.session_state.messages:
#     with st.chat_message(message.role):
#         st.markdown(message.content)

# Chat Input
if prompt := st.chat_input("How can I help with your order or product search?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response_placeholder = st.empty()

        # 1. Initial LLM Call
        chat_completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": m["role"], "content": m["content"]}
                      for m in st.session_state.messages],
            tools=TOOLS,
            tool_choice="auto"
        )

        msg = chat_completion.choices[0].message

        # 2. Check if Tool Call is needed
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                t_name = tool_call.function.name
                t_args = json.loads(tool_call.function.arguments)

                with st.status(f"🛠️ Using tool: {t_name}...", expanded=False):
                    tool_output = call_mcp_server(t_name, t_args)
                    st.write(tool_output)

                # Add tool result to history
                st.session_state.messages.append(msg)
                st.session_state.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": t_name,
                    "content": tool_output
                })

            # 3. Final synthesis
            # 3. Final synthesis
            # We ensure every message in the list is a dictionary for the API call
            formatted_messages = []
            for m in st.session_state.messages:
                if hasattr(m, "role"):  # If it's a Groq object
                    formatted_messages.append(
                        {"role": m.role, "content": m.content or ""})
                else:  # If it's already a dictionary
                    formatted_messages.append(m)

            final_res = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=formatted_messages
            )
            ans = final_res.choices[0].message.content

        response_placeholder.markdown(ans)
        st.session_state.messages.append({"role": "assistant", "content": ans})
