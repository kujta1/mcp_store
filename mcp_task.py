import asyncio
import httpx
import json

URL = "https://vipfapwm3x.us-east-1.awsapprunner.com/mcp"


async def fixed_inspect():
    print(f"Probing MCP Endpoint with strict headers: {URL}")
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # 1. Initialize session
            init_payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "prototype-client", "version": "1.0.0"}
                }
            }

            print("📤 Sending 'initialize' request...")
            response = await client.post(URL, json=init_payload, headers=headers)

            if response.status_code != 200:
                print(
                    f"❌ Server returned {response.status_code}: {response.text}")
                return

            print("✅ Initialized! Reading response...")
            # Some servers require the session ID for subsequent calls
            session_id = response.headers.get("mcp-session-id")
            if session_id:
                headers["mcp-session-id"] = session_id

            # 2. List Tools
            print("📤 Requesting tool list...")
            tools_payload = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }

            tools_resp = await client.post(URL, json=tools_payload, headers=headers)

            data = tools_resp.json()
            print("\n" + "="*40)
            print("🚀 SUCCESS! DISCOVERED TOOLS:")
            print("="*40)

            # Navigate the JSON-RPC response structure
            if "result" in data and "tools" in data["result"]:
                for tool in data["result"]["tools"]:
                    print(f"\n🛠️ Name: {tool['name']}")
                    print(f"📝 Description: {tool['description']}")
            else:
                print("Response received but no tools found. Raw response:")
                print(json.dumps(data, indent=2))

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(fixed_inspect())
