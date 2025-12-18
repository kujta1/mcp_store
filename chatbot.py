import chainlit as cl
import google.generativeai as genai
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import os

# Configure LLM (Gemini 1.5 Flash)
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
model = genai.GenerativeModel('gemini-1.5-flash')

MCP_URL = "https://vipfapwm3x.us-east-1.awsapprunner.com/mcp"


@cl.on_chat_start
async def start():
    # Establish MCP connection context
    cl.user_session.set("history", [])
    await cl.Message(content="Hello! I am the Support Bot. How can I help you with our computer products?").send()


@cl.on_message
async def main(message: cl.Message):
    history = cl.user_session.get("history")

    # 1. Connect to MCP Server to get current tools
    async with sse_client(MCP_URL) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            mcp_tools = await session.list_tools()

            # 2. Convert MCP tools to a format the LLM understands
            # (In a real implementation, you map these schemas to the LLM's function calling format)
            # For this prototype, we'll append tool descriptions to the system prompt
            tool_descriptions = "\n".join(
                [f"- {t.name}: {t.description}" for t in mcp_tools.tools])

            prompt = f"""
            You are a helpful support agent for a computer store.
            You have access to these tools:
            {tool_descriptions}
            
            If the user asks something requiring a tool, output the tool name and arguments.
            Otherwise, answer politely.
            
            User: {message.content}
            """

            # 3. Call LLM
            response = model.generate_content(prompt)

            # 4. (Simple Logic) If LLM suggests a tool, CALL IT via MCP
            # Note: A full implementation requires parsing the LLM function call JSON
            # and executing `await session.call_tool(name, arguments)`

            await cl.Message(content=response.text).send()
