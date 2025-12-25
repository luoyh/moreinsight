
from src.sql_agent import SQLAgent
from src.sql_tools import SQLTools
from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from dotenv import load_dotenv
import os
import asyncio
load_dotenv()

sql_tools = SQLTools()

root_agent = Agent(
    name='SQLToolAgent',
    model=LiteLlm(
        model='deepseek/deepseek-chat',
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_tokens=1024,
    ),
    tools = [sql_tools.get_all_table_names, sql_tools.get_table_schema, sql_tools.execute_query, sql_tools.format_result],
)


session_service = InMemorySessionService()

async def main():
    print("Hello from insight!")
    session = await session_service.create_session(
        app_name='SQLTools',
        user_id='USER_ID',
        session_id='SESSION_ID',
    )
    print(session)
    runner = Runner(
        agent=root_agent, # The agent we want to run
        app_name='sqlTools',   # Associates runs with our app
        session_service=session_service # Uses our session manager
    )
    print(f"Session ID: {session.id}")
    # agent = SQLAgent()
    # result = agent.process_query("查询所有评论")
    # print(result)
    history = []
    while True:
        user_input = input("请输入您的查询（输入exit退出）：")
        if user_input.lower() == 'exit':
            break
        # result = agent.run_async(user_input)
        # history.append({"user": user_input, "assistant": result})
        
        final_response_text = "No response received"
        async for event in runner.run_async(user_id='USER_ID', session_id='SESSION_ID', new_message=types.Content(role='user', parts=[types.Part(text=user_input)])):
            print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_response_text = event.content.parts[0].text
                elif event.actions and event.actions.escalate:
                    final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
                break
        print(f"<<< Agent Response: {final_response_text}")

if __name__ == "__main__":
    asyncio.run(main())
