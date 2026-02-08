"""
测试 tron_get_account_tokens MCP 工具
=====================================

覆盖账户代币查询的各种场景：
- 参数校验（缺失、格式错误）
- 代币列表解析（TRX、TRC20、TRC10）
- 余额计算和格式化
- token_count 统计
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

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


class TestAccountTokensHandler(unittest.TestCase):
    """测试 call_router._handle_get_account_tokens"""

    def test_missing_address_param(self):
        """缺少 address 参数时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_tokens", {})
        self.assertIn("error", result)
        self.assertIn("address", result.get("summary", ""))

    def test_invalid_address_format(self):
        """无效地址格式时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_tokens", {
            "address": "invalid_address_123"
        })
        self.assertIn("error", result)
        self.assertIn("地址", result.get("summary", ""))

    @patch('tron_mcp_server.tron_client._get_account')
    def test_successful_query(self, mock_get_account):
        """正常查询成功（mock _get_account 响应）"""
        from tron_mcp_server import call_router
        
        # Mock TRONSCAN /api/account 响应
        mock_get_account.return_value = {
            "balance": 5000000,  # 5 TRX (in SUN)
            "trc20token_balances": [
                {
                    "tokenId": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
                    "tokenName": "Tether USD",
                    "tokenAbbr": "USDT",
                    "balance": "50000000",  # 50 USDT
                    "tokenDecimal": 6,
                    "tokenLogo": "https://example.com/usdt.png"
                },
                {
                    "tokenId": "TSSMHYeV2uE9qYH95DqyoCuNCzEL1NvU3S",
                    "tokenName": "SUN Token",
                    "tokenAbbr": "SUN",
                    "balance": "1000000000000",  # 1000000 SUN
                    "tokenDecimal": 6
                }
            ],
            "tokenBalances": []
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertIn("tokens", result)
        self.assertIn("token_count", result)
        self.assertIn("summary", result)

    @patch('tron_mcp_server.tron_client._get_account')
    def test_result_includes_trx_entry(self, mock_get_account):
        """结果中至少包含 TRX 条目"""
        from tron_mcp_server import call_router
        
        mock_get_account.return_value = {
            "balance": 10000000,  # 10 TRX
            "trc20token_balances": []
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        tokens = result.get("tokens", [])
        self.assertTrue(len(tokens) >= 1)
        
        # 验证 TRX 条目
        trx_token = next((t for t in tokens if t["token_abbr"] == "TRX"), None)
        self.assertIsNotNone(trx_token, "结果应包含 TRX 条目")
        self.assertEqual(trx_token["token_type"], "native")
        self.assertEqual(trx_token["decimals"], 6)
        self.assertEqual(trx_token["balance"], 10.0)

    @patch('tron_mcp_server.tron_client._get_account')
    def test_trc20_token_parsing(self, mock_get_account):
        """TRC20 代币正确解析（名称、余额、小数位）"""
        from tron_mcp_server import call_router
        
        mock_get_account.return_value = {
            "balance": 0,
            "trc20token_balances": [
                {
                    "tokenId": "USDT_CONTRACT_ADDR",
                    "tokenName": "Tether USD",
                    "tokenAbbr": "USDT",
                    "balance": "123456789",  # 123.456789 USDT
                    "tokenDecimal": 6
                },
                {
                    "tokenId": "JST_CONTRACT_ADDR",
                    "tokenName": "JUST Token",
                    "tokenAbbr": "JST",
                    "balance": "987654321000000000",  # 0.987654321 JST (18 decimals)
                    "tokenDecimal": 18
                }
            ]
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        tokens = result.get("tokens", [])
        
        # 验证 USDT
        usdt = next((t for t in tokens if t["token_abbr"] == "USDT"), None)
        self.assertIsNotNone(usdt)
        self.assertEqual(usdt["token_type"], "trc20")
        self.assertEqual(usdt["token_name"], "Tether USD")
        self.assertEqual(usdt["decimals"], 6)
        self.assertAlmostEqual(usdt["balance"], 123.456789, places=6)
        self.assertEqual(usdt["contract_address"], "USDT_CONTRACT_ADDR")
        
        # 验证 JST
        jst = next((t for t in tokens if t["token_abbr"] == "JST"), None)
        self.assertIsNotNone(jst)
        self.assertEqual(jst["token_type"], "trc20")
        self.assertEqual(jst["decimals"], 18)
        self.assertAlmostEqual(jst["balance"], 0.987654321, places=9)

    @patch('tron_mcp_server.tron_client._get_account')
    def test_token_count_accuracy(self, mock_get_account):
        """token_count 统计正确"""
        from tron_mcp_server import call_router
        
        mock_get_account.return_value = {
            "balance": 1000000,  # 1 TRX
            "trc20token_balances": [
                {"tokenId": "T1", "tokenName": "Token1", "tokenAbbr": "TK1", "balance": "1000000", "tokenDecimal": 6},
                {"tokenId": "T2", "tokenName": "Token2", "tokenAbbr": "TK2", "balance": "2000000", "tokenDecimal": 6},
                {"tokenId": "T3", "tokenName": "Token3", "tokenAbbr": "TK3", "balance": "3000000", "tokenDecimal": 6},
            ]
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        # 应该有 1 个 TRX + 3 个 TRC20 = 4 个代币
        self.assertEqual(result["token_count"], 4)
        self.assertEqual(len(result["tokens"]), 4)

    @patch('tron_mcp_server.tron_client._get_account')
    def test_zero_balance_trx(self, mock_get_account):
        """TRX 余额为 0 时也应包含在结果中"""
        from tron_mcp_server import call_router
        
        mock_get_account.return_value = {
            "balance": 0,  # 0 TRX
            "trc20token_balances": []
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        tokens = result.get("tokens", [])
        self.assertEqual(len(tokens), 1)  # 只有 TRX
        self.assertEqual(tokens[0]["token_abbr"], "TRX")
        self.assertEqual(tokens[0]["balance"], 0.0)

    @patch('tron_mcp_server.tron_client._get_account')
    def test_formatted_summary(self, mock_get_account):
        """格式化后的 summary 包含关键信息"""
        from tron_mcp_server import call_router
        
        mock_get_account.return_value = {
            "balance": 100000000,  # 100 TRX
            "trc20token_balances": [
                {"tokenId": "USDT_ADDR", "tokenName": "USDT", "tokenAbbr": "USDT", "balance": "50000000", "tokenDecimal": 6}
            ]
        }
        
        result = call_router.call("get_account_tokens", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        summary = result.get("summary", "")
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        # 验证 summary 包含代币数量信息
        self.assertIn("2", summary)  # 2 种代币
        self.assertIn("代币", summary)


class TestAccountTokensTool(unittest.TestCase):
    """测试 server.py 中的 tron_get_account_tokens MCP 工具"""

    def test_tool_exists(self):
        """验证 tron_get_account_tokens 工具已注册"""
        from tron_mcp_server import server
        
        self.assertTrue(hasattr(server, 'tron_get_account_tokens'))


if __name__ == '__main__':
    unittest.main()
