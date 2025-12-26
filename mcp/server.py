import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import os
import json
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel, Field
import asyncio
from mcp.server.fastmcp import FastMCP
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("mysql_mcp_server")
file_handler = logging.FileHandler(filename=".logs/mcp_server.log",encoding="utf-8")
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logger.addHandler(file_handler)
load_dotenv()
mcp = FastMCP("mysql_mcp_server")

def get_db_config():
    return {
        'host': os.getenv("MYSQL_HOST"),
        'port': int(os.getenv("MYSQL_PORT")),
        'user': os.getenv("MYSQL_USER"),
        'password': os.getenv("MYSQL_PASSWORD"),
        'database': os.getenv("MYSQL_DATABASE")
    }

@mcp.prompt(title="MySQL数据库智能查询助手")
async def get_system_prompt() -> str:
        """系统提示词：定义Agent的行为逻辑"""
        return """
        你是一个MySQL数据库智能查询助手，能够根据用户问题调用对应的工具获取数据库信息：
        1. 当用户问"有哪些表"、"表列表"等问题时，调用get_all_table_info工具
        2. 当用户问某个表的结构、作用、数据量、数据时，调用get_table_detail工具（需要指定table_name参数）
        3. 可以根据用户需求生成SQL语句,调用execute_query工具执行返回结果并分析
        4. 回答时要清晰、结构化，使用中文，数据展示要易读
        5. 如果工具调用失败或无数据，要友好提示
        """

def connect_mysql():
    """连接MySQL数据库"""
    config = get_db_config()
    mysql_conn = mysql.connector.connect(**config)  
    return mysql_conn


@mcp.tool(title="执行MySQL查询")
async def execute_query(query: str, params: tuple = None) -> list:
    """执行查询并返回结果"""
    logger.info(f"执行查询: {query}")
    result = []
    try:
        with connect_mysql() as mysql_conn:
            cursor = mysql_conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
    except Error as e:
        logger.error(f"查询执行失败: {e}")
        return []

@mcp.tool(title="获取MySQL数据库所有表名")
async def get_tables() -> list:
    """获取数据库中所有表名"""
    query = """
    SELECT table_name 
    FROM information_schema.tables 
    WHERE table_schema = %s AND table_type = 'BASE TABLE'
    """
    result = await execute_query(query, (mysql_conn.config.database,))
    return [item["TABLE_NAME"] for item in result]
    
@mcp.tool(title="获取MySQL数据库表结构")
async def get_table_structure(table_name: str) -> list:
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
    result = await execute_query(query, (mysql_conn.config.database, table_name))
    return result

@mcp.tool(title="获取MySQL数据库表注释")
async def get_table_comment(table_name: str) -> str:
    """获取表的注释（表的作用）"""
    query = """
    SELECT table_comment 
    FROM information_schema.tables 
    WHERE table_schema = %s AND table_name = %s
    """
    result = await execute_query(query, (mysql_conn.config.database, table_name))
    return result[0]["TABLE_COMMENT"] if result else "无注释"

@mcp.tool(title="获取MySQL数据库表数据量")
async def get_table_row_count(table_name: str) -> int:  
    """获取指定表的数据量"""
    query = f"SELECT COUNT(*) AS count FROM {table_name}"
    result = await execute_query(query) 
    return result[0]["count"] if result else 0

@mcp.tool(title="获取MySQL数据库表前N行数据")
async def get_table_top_rows(table_name: str, sort_by: str = "create_time", sort_method: str = "desc", limit: int = 10) -> list:
    """获取指定表的前N行数据，默认按创建时间(create_time)倒序排序"""
    query = f"SELECT * FROM {table_name} ORDER BY {sort_by} {sort_method} LIMIT %s"
    result = await execute_query(query, (limit,))
    return result


if __name__ == "__main__":
    asyncio.run(mcp.run())
    # asyncio.run(mcp.serve(host="0.0.0.0",port=8000))