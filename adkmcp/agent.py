# ./adk_agent_samples/mcp_client_agent/agent.py
import os
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents import Agent
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# IMPORTANT: Replace this with the ABSOLUTE path to your my_adk_mcp_server.py script
PATH_TO_YOUR_MCP_SERVER_SCRIPT = "e:/.roy/data/code/tmp/insight/mcp/server.py" # <<< REPLACE

print("PATH_TO_YOUR_MCP_SERVER_SCRIPT:", PATH_TO_YOUR_MCP_SERVER_SCRIPT)

root_agent = Agent(
    name="moreinsightAgentADK",
    model=LiteLlm(
        model="deepseek/deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_tokens=1024,
    ),
    description=(
        "一个可查询数据库数据并分析的智能助手"
    ),
    instruction=(
        "一个可查询数据库数据并分析的智能助手"
    ),
    tools=[
        McpToolset(
            connection_params=StdioConnectionParams(
                server_params = StdioServerParameters(
                    command='uv',
                    args=["run", PATH_TO_YOUR_MCP_SERVER_SCRIPT]
                )
            )
            # tool_filter=['load_web_page'] # Optional: ensure only specific tools are loaded
        )
    ],
)