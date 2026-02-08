"""
Pytest 共享配置和 fixtures
=======================

为所有测试提供统一的：
- 项目路径设置
- mcp 依赖 mock
- 通用测试数据
"""

import sys
import os
import unittest.mock as mock

# 必须导入 pytest，否则装饰器会报错
try:
    import pytest
except ImportError:
    print("错误: pytest 未安装")
    print("请运行: pip install pytest pytest-asyncio")
    sys.exit(1)

# 设置项目根目录路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 自动 mock mcp 依赖，防止导入 server.py 时出错
sys.modules["mcp"] = mock.MagicMock()
sys.modules["mcp.server"] = mock.MagicMock()
sys.modules["mcp.server.fastmcp"] = mock.MagicMock()


# ============ 通用 fixtures ============

@pytest.fixture
def mock_mcp():
    """提供 mock 的 mcp 模块"""
    return sys.modules["mcp"]


@pytest.fixture
def sample_tron_address():
    """示例 TRON 地址"""
    return "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"


@pytest.fixture
def sample_hex_address():
    """示例 Hex 地址（0x 前缀）"""
    return "0x41a2b3c4d5e6f708090a0b0c0d0e0f101112131415"


@pytest.fixture
def sample_tx_hash():
    """示例交易哈希"""
    return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


@pytest.fixture
def sample_usdt_contract():
    """示例 USDT 合约地址"""
    return "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # TRC20 USDT on Nile


# ============ 环境变量 fixtures ============

@pytest.fixture
def clean_env(monkeypatch):
    """清理环境变量，提供干净的测试环境"""
    vars_to_clear = [
        "TRONSCAN_API_URL",
        "TRONSCAN_API_KEY",
        "TRONSCAN_TIMEOUT",
        "DEFAULT_NETWORK",
        "PRIVATE_KEY",
        "WALLET_ADDRESS",
    ]
    for var in vars_to_clear:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


# ============ 测试数据加载器 ============

def load_test_data(filename):
    """从 tests/fixtures/ 加载测试数据 JSON 文件"""
    import json
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    filepath = os.path.join(fixtures_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


# ============ 断言辅助函数 ============

def assert_valid_tron_address(address):
    """断言地址是有效的 TRON 地址格式"""
    assert address.startswith("T") or address.startswith("0x41"), \
        f"Invalid TRON address: {address}"
    if address.startswith("T"):
        assert len(address) == 34, f"Base58 address should be 34 chars: {address}"
    else:
        assert len(address) == 42, f"Hex address should be 42 chars: {address}"


def assert_valid_tx_hash(txid):
    """断言交易哈希格式正确"""
    assert txid.startswith("0x"), f"Txid should start with 0x: {txid}"
    assert len(txid) == 66, f"Txid should be 66 chars (0x + 64 hex): {txid}"


# ============ 自动标记测试 ============

def pytest_collection_modifyitems(config, items):
    """根据测试文件所在目录自动添加标记"""
    for item in items:
        # 获取测试文件路径
        test_path = str(item.fspath)
        # 根据目录添加标记
        if "/tests/unit/" in test_path or "\\tests\\unit\\" in test_path:
            item.add_marker(pytest.mark.unit)
        elif "/tests/integration/" in test_path or "\\tests\\integration\\" in test_path:
            item.add_marker(pytest.mark.integration)
        elif "/tests/functional/" in test_path or "\\tests\\functional\\" in test_path:
            item.add_marker(pytest.mark.functional)
        elif "/tests/regression/" in test_path or "\\tests\\regression\\" in test_path:
            item.add_marker(pytest.mark.regression)
        elif "/tests/stress/" in test_path or "\\tests\\stress\\" in test_path:
            item.add_marker(pytest.mark.stress)
