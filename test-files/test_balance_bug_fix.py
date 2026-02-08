"""
测试 Bug Fix: get_balance_trx() 新地址查询异常修复
======================================================

验证 get_balance_trx() 在查询新地址（API 返回空对象）时：
- 不再抛出 ValueError("缺少数值字段")
- 正确返回余额 0
"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

os.chdir("../tron-mcp-server")

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import tron_client


class TestGetBalanceTrxBugFix(unittest.TestCase):
    """测试 get_balance_trx() 新地址查询 Bug 修复"""

    @patch('tron_mcp_server.tron_client._get')
    def test_new_address_returns_zero_balance(self, mock_get):
        """新地址（所有余额字段缺失）应返回 0 而非抛异常"""
        # 模拟 API 返回：新地址，所有余额字段都不存在
        mock_get.return_value = {
            "address": "TNewAddressNeverUsedBefore123456789",
            # 注意：balance, balanceSun, totalBalance, total_balance 全部缺失
        }
        
        # 修复前：_first_not_none() 返回 None，_to_int(None) 抛 ValueError
        # 修复后：_first_not_none(..., 0) 返回 0，正常返回余额 0
        balance = tron_client.get_balance_trx("TNewAddressNeverUsedBefore123456789")
        
        self.assertEqual(balance, 0.0, "新地址余额应为 0")
        mock_get.assert_called_once()

    @patch('tron_mcp_server.tron_client._get')
    def test_existing_address_returns_correct_balance(self, mock_get):
        """已有余额的地址应正常返回余额"""
        # 模拟 API 返回：地址有余额
        mock_get.return_value = {
            "address": "TExistingAddressWithBalance",
            "balance": 1000000,  # 1 TRX (in SUN)
        }
        
        balance = tron_client.get_balance_trx("TExistingAddressWithBalance")
        
        self.assertEqual(balance, 1.0, "应返回 1.0 TRX")
        mock_get.assert_called_once()

    @patch('tron_mcp_server.tron_client._get')
    def test_zero_balance_address(self, mock_get):
        """余额为 0 的地址应返回 0"""
        # 模拟 API 返回：地址存在但余额为 0
        mock_get.return_value = {
            "address": "TAddressWithZeroBalance",
            "balance": 0,
        }
        
        balance = tron_client.get_balance_trx("TAddressWithZeroBalance")
        
        self.assertEqual(balance, 0.0, "余额为 0 的地址应返回 0.0")
        mock_get.assert_called_once()

    @patch('tron_mcp_server.tron_client._get')
    def test_balance_field_variants(self, mock_get):
        """测试不同的余额字段名称变体"""
        test_cases = [
            ({"balanceSun": 2000000}, 2.0),
            ({"totalBalance": 3000000}, 3.0),
            ({"total_balance": 4000000}, 4.0),
        ]
        
        for api_response, expected_balance in test_cases:
            with self.subTest(field=list(api_response.keys())[0]):
                api_response["address"] = "TTestAddress"
                mock_get.return_value = api_response
                
                balance = tron_client.get_balance_trx("TTestAddress")
                
                self.assertEqual(balance, expected_balance)


if __name__ == "__main__":
    unittest.main()
