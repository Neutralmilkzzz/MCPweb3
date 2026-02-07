"""配置模块

通过 TRON_NETWORK 环境变量切换主网 (mainnet) / 测试网 (nile)。
各模块应调用本模块的函数获取网络相关的默认值，
用户在 .env 中显式设置的值始终优先。
"""

import os
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# ============ 网络预设 ============

_NETWORK_PRESETS = {
    "mainnet": {
        "TRONSCAN_API_URL": "https://apilist.tronscan.org/api",
        "TRONGRID_API_URL": "https://api.trongrid.io",
        "USDT_CONTRACT_ADDRESS": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
        "USDT_CONTRACT_ADDRESS_HEX": "41a614f803b6fd780986a42c78ec9c7f77e6ded13c",
    },
    "nile": {
        "TRONSCAN_API_URL": "https://nileapi.tronscan.org/api",
        "TRONGRID_API_URL": "https://nile.trongrid.io",
        "USDT_CONTRACT_ADDRESS": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
        "USDT_CONTRACT_ADDRESS_HEX": "41eca9bc828a3005b9a3b909f2cc5c2a54794de05f",
    },
}


def get_network() -> str:
    """获取当前网络名称 (mainnet / nile)"""
    return os.getenv("TRON_NETWORK", "mainnet").strip().lower()


def _preset(key: str) -> str:
    """根据当前网络返回预设值"""
    network = get_network()
    presets = _NETWORK_PRESETS.get(network, _NETWORK_PRESETS["mainnet"])
    return presets[key]


# ============ API 配置 ============


def get_api_url() -> str:
    """获取 TRONSCAN API URL（用户显式设置优先）"""
    return os.getenv("TRONSCAN_API_URL", "") or _preset("TRONSCAN_API_URL")


def get_trongrid_url() -> str:
    """获取 TronGrid API URL（用户显式设置优先）"""
    url = os.getenv("TRONGRID_API_URL", "") or _preset("TRONGRID_API_URL")
    return url.rstrip("/")


def get_api_key() -> str:
    """获取 TRONSCAN API KEY"""
    return os.getenv("TRONSCAN_API_KEY", "")


def get_trongrid_api_key() -> str:
    """获取 TRONGRID API KEY（回退到 TRONSCAN_API_KEY）"""
    return os.getenv("TRONGRID_API_KEY", "") or get_api_key()


def get_timeout() -> float:
    """获取请求超时时间"""
    return float(os.getenv("REQUEST_TIMEOUT", "10.0"))


# ============ 合约地址 ============


def get_usdt_contract() -> str:
    """获取 USDT TRC20 合约地址 (Base58)"""
    return os.getenv("USDT_CONTRACT_ADDRESS", "") or _preset("USDT_CONTRACT_ADDRESS")


def get_usdt_contract_hex() -> str:
    """获取 USDT TRC20 合约地址 (Hex, 不含 0x)"""
    return os.getenv("USDT_CONTRACT_ADDRESS_HEX", "") or _preset("USDT_CONTRACT_ADDRESS_HEX")
