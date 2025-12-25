# -*- coding: utf-8 -*-
# sql_agent.py - SQL智能代理
import mysql.connector
import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
import os

class SQLTools:
    def __init__(self):
        # 初始化数据库连接
        self.db_config = {
            'host': os.getenv("MYSQL_HOST"),
            'user': os.getenv("MYSQL_USER"),
            'port': int(os.getenv("MYSQL_PORT")),
            'password': os.getenv("MYSQL_PASSWORD"),
            'database': os.getenv("MYSQL_DATABASE")
        }
        
        # 定义数据库模式
        self.schema_info = """
        Database: insight
        """
    
    def generate_sql(self, natural_query):
        """将自然语言转换为SQL查询"""
        prompt = ChatPromptTemplate.from_messages([
            ("system", f"你是一个SQL生成助手。根据用户的问题生成相应的MySQL查询语句。数据库模式如下：\n{self.schema_info}\n只返回SQL语句，不要其他内容。"),
            ("human", natural_query)
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({"natural_query": natural_query})
        
        # 提取SQL语句
        sql_match = re.search(r'SELECT.*?;', response.content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            return sql_match.group(0).strip()
        else:
            # 如果没有找到完整SQL，尝试直接返回
            sql_match_alt = re.search(r'(SELECT|INSERT|UPDATE|DELETE).*?;', response.content, re.DOTALL | re.IGNORECASE)
            if sql_match_alt:
                return sql_match_alt.group(0).strip()
            else:
                return response.content.strip()

    def get_all_table_names(self):
        """获取数据库所有表名"""
        df = self.execute_query("SHOW TABLES;")
        return df['Tables_in_insight'].tolist()

    def get_table_schema(self, table_name):
        """获取表的建表语句"""
        df = self.execute_query(f"SHOW CREATE TABLE {table_name};")
        return df['Create Table'][0]

    def execute_query(self, sql_query):
        """执行SQL查询"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            df = pd.read_sql(sql_query, conn)
            conn.close()
            return df
        except Exception as e:
            raise e
    
    def format_result(self, result_df, original_query):
        """格式化查询结果"""
        if result_df.empty:
            return "未找到相关数据"
        
        # 使用AI解释结果
        result_str = result_df.to_string(max_rows=10, max_cols=10)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "你是一个数据分析助手，请用自然语言解释表格数据的结果。"),
            ("human", f"原始问题：{original_query}\n\n数据结果：\n{result_str}\n\n请用中文解释这些数据的含义。")
        ])
        
        chain = prompt | self.llm
        response = chain.invoke({})
        
        return response.content