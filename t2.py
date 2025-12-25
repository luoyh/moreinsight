from src.sql_agent import SQLAgent
from src.sql_tools import SQLTools
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai.types import Content, Part
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

sql_tools = SQLTools()

# 初始化Agent
agent = Agent(
    name='SQLToolAgent',
    model=LiteLlm(
        model='deepseek/deepseek-chat',
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_tokens=1024,
    ),
    tools = [
        sql_tools.get_all_table_names,
        sql_tools.get_table_schema,
        sql_tools.execute_query,
        sql_tools.format_result
    ],
)

async def main():
    print("Hello from insight!")
    history = []
    while True:
        user_input = input("\n请输入您的查询（输入exit退出）：")
        if user_input.lower() == 'exit':
            break

        final_response_text = "No response received"
        try:
            # 构建对话上下文
            messages = [Content(role='user', parts=[Part(text=user_input)])]
            # 直接调用Agent的generate_async方法（绕过Runner/Session）
            async for event in agent.generate_async(messages=messages):
                print(f"  [Event] 类型: {type(event).__name__}, 最终响应: {event.is_final_response()}, 内容: {event.content}")
                if event.is_final_response():
                    if event.content and event.content.parts:
                        final_response_text = event.content.parts[0].text
                    break

            print(f"\n<<< Agent 回复: {final_response_text}")
            history.append({"user": user_input, "assistant": final_response_text})

        except Exception as e:
            print(f"\n❌ 错误: {type(e).__name__}: {str(e)}")
            continue

if __name__ == "__main__":
    asyncio.run(main())