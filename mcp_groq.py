import os
import json
import httpx
from groq import Groq

# Initialize Groq Client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"
MCP_URL = "https://vipfapwm3x.us-east-1.awsapprunner.com/mcp"

# 1. Define the Tools for Groq (Using the schema we discovered)
# You would repeat this for list_products, get_order, etc.
tools = [
    {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "List products with optional filters like category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "e.g. Computers, Monitors"}
                }
            }
        }
    }
]


async def call_mcp_server(tool_name, arguments):
    """The bridge to the MCP server we debugged earlier"""
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
    payload = {
        "jsonrpc": "2.0",
        "id": "1",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": arguments}
    }
    async with httpx.AsyncClient() as http_client:
        response = await http_client.post(MCP_URL, json=payload, headers=headers)
        # MCP returns content in a specific 'content' field
        return response.json().get("result", {}).get("content", "No data found.")

# 2. The Chat Loop (Simplified for Demo)


async def chat_with_support(user_input):
    messages = [{"role": "user", "content": user_input}]

    # First call to Groq to see if it wants to use a tool
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )

    response_message = response.choices[0].message

    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            # Call our MCP Bridge
            tool_result = await call_mcp_server(
                tool_call.function.name,
                json.loads(tool_call.function.arguments)
            )

            # Send result back to Groq for final answer
            messages.append(response_message)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": tool_call.function.name,
                "content": str(tool_result)
            })

            final_response = client.chat.completions.create(
                model=MODEL,
                messages=messages
            )
            return final_response.choices[0].message.content

    return response_message.content
