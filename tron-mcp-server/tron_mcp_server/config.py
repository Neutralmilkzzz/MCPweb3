"""配置模块"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


def get_api_url() -> str:
    """获取 TRONSCAN API URL"""
    return os.getenv("TRONSCAN_API_URL", "")


def get_api_key() -> str:
    """获取 TRONSCAN API KEY"""
    return os.getenv("TRONSCAN_API_KEY", "")


def get_timeout() -> float:
    """获取请求超时时间"""
    return float(os.getenv("REQUEST_TIMEOUT", "10.0"))
