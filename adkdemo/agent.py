import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from dotenv import load_dotenv
import os
import json
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel, Field

load_dotenv()

# 关键：导入LiteLLM适配器
from google.adk.models.lite_llm import LiteLlm



# mysql config
class MySQLConfig(BaseModel):
    host: str = Field(..., description="数据库主机地址")
    port: int = Field(3306, description="数据库端口")
    user: str = Field(..., description="数据库用户名")
    password: str = Field(..., description="数据库密码")
    database: str = Field(..., description="数据库名称")

# mysql 数据库操作类
class MySQLHandler:
    def __init__(self, config: MySQLConfig):
        self.config = config
        self.connection = None

    def connect(self):
        """建立数据库连接"""
        try:
            self.connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                user=self.config.user,
                password=self.config.password,
                database=self.config.database,
                charset="utf8mb4"
            )
            if self.connection.is_connected():
                return True
        except Error as e:
            print(f"数据库连接失败: {e}")
            return False

    def close(self):
        """关闭数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()

    def execute_query(self, query: str, params: tuple = None) -> list:
        """执行查询并返回结果"""
        result = []
        try:
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            print(f"查询执行失败: {e}")
            return []

    def get_tables(self) -> list:
        """获取数据库中所有表名"""
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        """
        result = self.execute_query(query, (self.config.database,))
        return [item["TABLE_NAME"] for item in result]

    def get_table_structure(self, table_name: str) -> list:
        """获取指定表的结构（字段名、类型、注释等）"""
        query = """
        SELECT 
            column_name AS field,
            data_type AS type,
            is_nullable AS nullable,
            column_default AS default_value,
            column_comment AS comment
        FROM information_schema.columns 
        WHERE table_schema = %s AND table_name = %s
        ORDER BY ordinal_position
        """
        return self.execute_query(query, (self.config.database, table_name))

    def get_table_comment(self, table_name: str) -> str:
        """获取表的注释（表的作用）"""
        query = """
        SELECT table_comment 
        FROM information_schema.tables 
        WHERE table_schema = %s AND table_name = %s
        """
        result = self.execute_query(query, (self.config.database, table_name))
        return result[0]["TABLE_COMMENT"] if result else "无注释"

    def get_table_row_count(self, table_name: str) -> int:
        """获取指定表的数据量"""
        query = f"SELECT COUNT(*) AS count FROM {table_name}"
        result = self.execute_query(query)
        return result[0]["count"] if result else 0

    def get_table_top_rows(self, table_name: str, sort_by: str = "create_time", sort_method: str = "desc", limit: int = 10) -> list:
        """获取指定表的前N行数据，默认按创建时间(create_time)倒序排序"""
        query = f"SELECT * FROM {table_name} ORDER BY {sort_by} {sort_method} LIMIT %s"
        return self.execute_query(query, (limit,))

# AI agent tools
class MySQLToolkit:
    def __init__(self, db_handler: MySQLHandler):
        self.db_handler = db_handler

    def get_all_table_info(self) -> dict:
        """获取所有表的基础信息（名称、注释、数据量）"""
        tables = self.db_handler.get_tables()
        table_info = {}
        for table in tables:
            table_info[table] = {
                "comment": self.db_handler.get_table_comment(table),
                "row_count": self.db_handler.get_table_row_count(table)
            }
        return table_info

    def execute_query(self, query: str, params: tuple = None) -> list:
        """执行SQL查询并返回结果"""
        return self.db_handler.execute_query(query, params)

    def get_table_detail(self, table_name: str, sort_by: str = "create_time", sort_method: str = "desc", limit: int = 10) -> dict:
        """获取指定表的完整信息（结构、注释、数据量、前N行数据）"""
        return {
            "table_name": table_name,
            "comment": self.db_handler.get_table_comment(table_name),
            "structure": self.db_handler.get_table_structure(table_name),
            "row_count": self.db_handler.get_table_row_count(table_name),
            "row_top_n": self.db_handler.get_table_top_rows(table_name=table_name, sort_by=sort_by, sort_method=sort_method, limit=limit)
        }

class MySQLAIAgent:
    def __init__(self, db_config: MySQLConfig):
        # 初始化数据库处理器
        self.db_handler = MySQLHandler(db_config)
        self.db_toolkit = MySQLToolkit(self.db_handler)
        # 连接数据库
        self.db_handler.connect()

    def _get_system_prompt(self) -> str:
        """系统提示词：定义Agent的行为逻辑"""
        return """
        你是一个MySQL数据库智能查询助手，能够根据用户问题调用对应的工具获取数据库信息：
        1. 当用户问"有哪些表"、"表列表"等问题时，调用get_all_table_info工具
        2. 当用户问某个表的结构、作用、数据量、数据时，调用get_table_detail工具（需要指定table_name参数）
        3. 可以根据用户需求生成SQL语句,调用execute_query工具执行返回结果并分析
        4. 回答时要清晰、结构化，使用中文，数据展示要易读
        5. 如果工具调用失败或无数据，要友好提示
        """


db_config = MySQLConfig(
    host=os.getenv("MYSQL_HOST"),
    port=int(os.getenv("MYSQL_PORT")),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASSWORD"),
    database=os.getenv("MYSQL_DATABASE")
)

# init Agent
agent = MySQLAIAgent(db_config)

# 核心配置：使用LiteLLM连接Deepseek模型
root_agent = Agent(
    name="sql_agent",
    model=LiteLlm(
        model="deepseek/deepseek-chat",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        max_tokens=1024,
    ),
    description=(
        "一个可查询数据库数据并分析的智能助手"
    ),
    instruction=(
        agent._get_system_prompt()
    ),
    tools=[agent.db_toolkit.get_all_table_info, agent.db_toolkit.get_table_detail, agent.db_toolkit.execute_query],
)
