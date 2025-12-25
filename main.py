
from src.sql_agent import SQLAgent
from src.sql_tools import SQLTools
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider

from dotenv import load_dotenv
import os
import asyncio
load_dotenv()

sql_tools = SQLTools()

model = OpenAIChatModel(
    'deepseek-chat',
    provider=DeepSeekProvider(api_key=os.getenv("DEEPSEEK_API_KEY")),
)
agent = Agent(
    model=model,
    tools = [sql_tools.get_all_table_names, sql_tools.get_table_schema, sql_tools.execute_query, sql_tools.format_result],
    system_prompt="你是一个SQL助手",
)

def main():
    print("Hello from insight!")
    # agent = SQLAgent()
    # result = agent.process_query("查询所有评论")
    # print(result)
    history = []
    while True:
        user_input = input("请输入您的查询（输入exit退出）：")
        if user_input.lower() == 'exit':
            break
        resp = agent.run_sync(user_prompt=user_input, message_history=history)
        history = list(resp.all_messages())
        print(resp.output)

if __name__ == "__main__":
    main()
