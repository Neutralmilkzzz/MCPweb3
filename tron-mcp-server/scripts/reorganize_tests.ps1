# 测试文件重组脚本
# 用法: cd tron-mcp-server; powershell -ExecutionPolicy Bypass -File scripts/reorganize_tests.ps1

Write-Host "开始重组测试文件..." -ForegroundColor Cyan

# 创建目录
$dirs = 'tests/unit', 'tests/integration', 'tests/functional', 'tests/regression', 'tests/stress', 'tests/fixtures'
foreach ($dir in $dirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "✓ 创建目录: $dir"
    }
}

# 定义文件分类
$fileMap = @{
    'unit' = @(
        'test_validators.py',
        'test_formatters.py',
        'test_key_manager.py'
    )
    'integration' = @(
        'test_trongrid_client.py',
        'test_tron_client.py',
        'test_tx_builder_new.py',
        'test_tx_builder_integration.py',
        'test_transfer_flow.py',
        'test_call_router_actions.py',
        'test_call_router_queries.py'
    )
    'functional' = @(
        'test_account_tokens.py',
        'test_account_resources.py',
        'test_address_book.py',
        'test_config_and_skills.py',
        'test_internal_transactions.py',
        'test_memo_functionality.py',
        'test_qrcode.py',
        'test_server_tools.py',
        'test_sign_broadcast.py',
        'test_sign_tx.py',
        'test_transaction_history.py'
    )
    'regression' = @(
        'test_balance_bug_fix.py',
        'test_known_issues.py'
    )
    'stress' = @(
        'stress_test.py'
    )
}

# 移动文件
foreach ($category in $fileMap.Keys) {
    foreach ($file in $fileMap[$category]) {
        if (Test-Path $file) {
            $dest = "tests/$category/$file"
            Move-Item $file $dest -Force
            Write-Host "✓ 移动: $file -> $dest"
        } else {
            Write-Host "⚠ 文件不存在: $file" -ForegroundColor Yellow
        }
    }
}

# 更新路径设置
Write-Host "`n更新路径设置..." -ForegroundColor Cyan
$testFiles = Get-ChildItem -Path tests -Recurse -Filter test_*.py, stress_test.py
foreach ($file in $testFiles) {
    $content = Get-Content $file.FullName -Raw
    $oldPattern = 'project_root = os\.path\.abspath\(os\.path\.join\(os\.path\.dirname\(__file__\), "\.\"\)\)'
    $newLine = 'project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))'
    $newContent = [regex]::Replace($content, $oldPattern, $newLine)

    if ($newContent -ne $content) {
        Set-Content $file.FullName -Value $newContent -Encoding UTF8
        Write-Host "✓ 更新路径: $($file.FullName)"
    }
}

# 创建conftest.py
$conftestPath = 'tests/conftest.py'
if (-not (Test-Path $conftestPath)) {
    $conftestContent = @'
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

# 自动 mock mcp 依赖
sys.modules["mcp"] = mock.MagicMock()
sys.modules["mcp.server"] = mock.MagicMock()
sys.modules["mcp.server.fastmcp"] = mock.MagicMock()


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
    """示例 Hex 地址"""
    return "0x41a2b3c4d5e6f708090a0b0c0d0e0f101112131415"


@pytest.fixture
def sample_tx_hash():
    """示例交易哈希"""
    return "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"


@pytest.fixture
def sample_usdt_contract():
    """示例 USDT 合约地址"""
    return "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"


@pytest.fixture
def clean_env(monkeypatch):
    """清理环境变量"""
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


def load_test_data(filename):
    """从 tests/fixtures/ 加载测试数据"""
    import json
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    filepath = os.path.join(fixtures_dir, filename)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def assert_valid_tron_address(address):
    """断言地址格式正确"""
    assert address.startswith("T") or address.startswith("0x41"), \
        f"Invalid TRON address: {address}"
    if address.startswith("T"):
        assert len(address) == 34, f"Base58 address should be 34 chars: {address}"
    else:
        assert len(address) == 42, f"Hex address should be 42 chars: {address}"


def assert_valid_tx_hash(txid):
    """断言交易哈希格式正确"""
    assert txid.startswith("0x"), f"Txid should start with 0x: {txid}"
    assert len(txid) == 66, f"Txid should be 66 chars: {txid}"
'@
    Set-Content $conftestPath -Value $conftestContent -Encoding UTF8
    Write-Host "✓ 创建: $conftestPath"
}

# 创建fixtures目录和示例数据
$fixturesDir = 'tests/fixtures'
if (-not (Test-Path $fixturesDir)) {
    New-Item -ItemType Directory -Path $fixturesDir -Force | Out-Null
    $sampleData = @'
{
  "tron_scan_account": {
    "success": true,
    "data": {
      "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
      "balance": 1234567890,
      "account_name": "Test Account",
      "create_time": 1640995200000,
      "latest_opration_time": 1704067200000
    }
  },
  "usdt_balance": {
    "success": true,
    "data": {
      "trc20": [
        {
          "contract_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
          "token_name": "Tether USD",
          "token_symbol": "USDT",
          "token_decimal": 6,
          "balance": "500000000"
        }
      ]
    }
  },
  "transaction_status": {
    "success": true,
    "data": {
      "txid": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
      "block_number": 12345678,
      "block_time_stamp": 1704067200000,
      "contract_ret": "SUCCESS",
      "fee": 1000000
    }
  }
}
'@
    Set-Content "$fixturesDir/sample_responses.json" -Value $sampleData -Encoding UTF8
    Write-Host "✓ 创建: $fixturesDir/sample_responses.json"
}

Write-Host "`n测试文件重组完成！" -ForegroundColor Green
Write-Host "运行: python run_tests.py --help 查看使用方法"
