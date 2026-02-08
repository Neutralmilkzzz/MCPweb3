"""
测试 tron_get_internal_transactions MCP 工具
=============================================

覆盖内部交易查询的各种场景：
- 参数校验（缺失、格式错误）
- limit 参数验证
- API 响应解析
- 格式化输出验证
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()


class TestInternalTransactionsHandler(unittest.TestCase):
    """测试 call_router._handle_get_internal_transactions"""

    def test_missing_address_param(self):
        """缺少 address 参数时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_internal_transactions", {})
        self.assertIn("error", result)
        self.assertIn("address", result.get("summary", ""))

    def test_invalid_address_format(self):
        """无效地址格式时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_internal_transactions", {
            "address": "invalid_address"
        })
        self.assertIn("error", result)
        self.assertIn("地址", result.get("summary", ""))

    def test_limit_validation_too_small(self):
        """limit 小于 1 时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "limit": 0
        })
        self.assertIn("error", result)
        self.assertIn("limit", result.get("summary", ""))

    def test_limit_validation_too_large(self):
        """limit 大于 50 时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "limit": 51
        })
        self.assertIn("error", result)
        self.assertIn("limit", result.get("summary", ""))

    @patch('tron_mcp_server.tron_client._get')
    def test_successful_query(self, mock_get):
        """正常查询成功（mock API 响应）"""
        from tron_mcp_server import call_router
        
        # Mock TRONSCAN API 响应
        mock_get.return_value = {
            "total": 42,
            "data": [
                {
                    "hash": "947d841d1cdd0b",
                    "timestamp": 1706822400000,
                    "callerAddress": "TYYYY1234567890123456789012345678",
                    "transferToAddress": "TZZZZ1234567890123456789012345678",
                    "callValueInfo": [
                        {
                            "callValue": 154000000,
                            "tokenId": "trx"
                        }
                    ],
                    "revert": False,
                    "note": None
                }
            ]
        }
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertIn("internal_transactions", result)
        self.assertIn("total", result)
        self.assertIn("summary", result)
        self.assertEqual(result["total"], 42)

    @patch('tron_mcp_server.tron_client._get')
    def test_formatted_result_includes_summary(self, mock_get):
        """格式化后的结果包含 summary"""
        from tron_mcp_server import call_router
        
        mock_get.return_value = {
            "total": 10,
            "data": [
                {
                    "hash": "abc123",
                    "timestamp": 1706822400000,
                    "callerAddress": "TAAAA1234567890123456789012345678",
                    "transferToAddress": "TBBBB1234567890123456789012345678",
                    "callValueInfo": [{"callValue": 100000000, "tokenId": "trx"}],
                    "revert": False
                }
            ]
        }
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "limit": 5
        })
        
        self.assertIn("summary", result)
        summary = result["summary"]
        self.assertIsInstance(summary, str)
        self.assertTrue(len(summary) > 0)
        # 确保 summary 包含关键信息
        self.assertIn("内部交易", summary)

    @patch('tron_mcp_server.tron_client._get')
    def test_default_limit_and_start(self, mock_get):
        """测试默认的 limit 和 start 参数"""
        from tron_mcp_server import call_router
        
        mock_get.return_value = {
            "total": 5,
            "data": []
        }
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        # 验证 API 调用使用了默认参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        self.assertEqual(params.get("limit"), 20)
        self.assertEqual(params.get("start"), 0)

    @patch('tron_mcp_server.tron_client._get')
    def test_custom_limit_and_start(self, mock_get):
        """测试自定义的 limit 和 start 参数"""
        from tron_mcp_server import call_router
        
        mock_get.return_value = {
            "total": 100,
            "data": []
        }
        
        result = call_router.call("get_internal_transactions", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "limit": 30,
            "start": 10
        })
        
        # 验证 API 调用使用了自定义参数
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        self.assertEqual(params.get("limit"), 30)
        self.assertEqual(params.get("start"), 10)


class TestInternalTransactionsTool(unittest.TestCase):
    """测试 server.py 中的 tron_get_internal_transactions MCP 工具"""

    def test_tool_exists(self):
        """验证 tron_get_internal_transactions 工具已注册"""
        from tron_mcp_server import server
        
        self.assertTrue(hasattr(server, 'tron_get_internal_transactions'))


if __name__ == '__main__':
    unittest.main()
