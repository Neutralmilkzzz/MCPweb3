"""
测试 tron_get_account_energy 和 tron_get_account_bandwidth MCP 工具
====================================================================

覆盖账户资源查询的各种场景：
- 参数校验（缺失、格式错误）
- Energy 查询（零能量、有能量、能量耗尽）
- Bandwidth 查询（仅免费带宽、有质押带宽）
- Formatters 测试
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


class TestAccountEnergyHandler(unittest.TestCase):
    """测试 call_router._handle_get_account_energy"""

    def test_missing_address_param(self):
        """缺少 address 参数时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_energy", {})
        self.assertIn("error", result)
        self.assertIn("address", result.get("summary", "").lower())

    def test_invalid_address_format(self):
        """无效地址格式时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_energy", {
            "address": "invalid_address_123"
        })
        self.assertIn("error", result)
        self.assertIn("地址", result.get("summary", ""))

    @patch('tron_mcp_server.trongrid_client._post')
    def test_zero_energy_account(self, mock_post):
        """查询零能量账户（未质押）"""
        from tron_mcp_server import call_router
        
        # Mock TronGrid /wallet/getaccountresource 响应 - 无能量
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 0,
            # 注意：未质押的账户不会有 EnergyLimit 和 NetLimit 字段
        }
        
        result = call_router.call("get_account_energy", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["energy_limit"], 0)
        self.assertEqual(result["energy_used"], 0)
        self.assertEqual(result["energy_remaining"], 0)
        self.assertIn("summary", result)
        self.assertIn("无能量额度", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_account_with_energy(self, mock_post):
        """查询有能量的账户"""
        from tron_mcp_server import call_router
        
        # Mock TronGrid /wallet/getaccountresource 响应 - 有能量
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 50,
            "EnergyLimit": 100000,
            "EnergyUsed": 35000,
            "NetLimit": 5000,
            "NetUsed": 100,
            "TotalEnergyLimit": 90000000000,
            "TotalEnergyWeight": 13369831825062,
        }
        
        result = call_router.call("get_account_energy", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["energy_limit"], 100000)
        self.assertEqual(result["energy_used"], 35000)
        self.assertEqual(result["energy_remaining"], 65000)
        self.assertIn("summary", result)
        self.assertIn("65,000", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_energy_exhausted(self, mock_post):
        """查询能量耗尽的账户"""
        from tron_mcp_server import call_router
        
        # Mock TronGrid /wallet/getaccountresource 响应 - 能量耗尽
        mock_post.return_value = {
            "freeNetLimit": 600,
            "EnergyLimit": 100000,
            "EnergyUsed": 100000,
        }
        
        result = call_router.call("get_account_energy", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["energy_remaining"], 0)
        self.assertIn("summary", result)
        self.assertIn("能量已耗尽", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_energy_with_usdt_transfer_estimate(self, mock_post):
        """有能量账户的 summary 应包含 USDT 转账估算"""
        from tron_mcp_server import call_router
        
        mock_post.return_value = {
            "freeNetLimit": 600,
            "EnergyLimit": 200000,
            "EnergyUsed": 5000,
        }
        
        result = call_router.call("get_account_energy", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        # 195000 / 65000 = 3 笔 USDT 转账
        self.assertIn("summary", result)
        self.assertIn("USDT 转账", result["summary"])
        self.assertIn("3", result["summary"])


class TestAccountBandwidthHandler(unittest.TestCase):
    """测试 call_router._handle_get_account_bandwidth"""

    def test_missing_address_param(self):
        """缺少 address 参数时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_bandwidth", {})
        self.assertIn("error", result)
        self.assertIn("address", result.get("summary", "").lower())

    def test_invalid_address_format(self):
        """无效地址格式时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("get_account_bandwidth", {
            "address": "bad_address"
        })
        self.assertIn("error", result)
        self.assertIn("地址", result.get("summary", ""))

    @patch('tron_mcp_server.trongrid_client._post')
    def test_only_free_bandwidth(self, mock_post):
        """仅有免费带宽的账户"""
        from tron_mcp_server import call_router
        
        # Mock TronGrid /wallet/getaccountresource 响应 - 仅免费带宽
        # 未质押的账户不会有 NetLimit 字段
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 100,
        }
        
        result = call_router.call("get_account_bandwidth", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["free_net_limit"], 600)
        self.assertEqual(result["free_net_used"], 100)
        self.assertEqual(result["free_net_remaining"], 500)
        self.assertEqual(result["net_limit"], 0)
        self.assertEqual(result["total_bandwidth"], 600)
        self.assertEqual(result["total_remaining"], 500)
        self.assertIn("summary", result)
        self.assertIn("免费带宽", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_with_staked_bandwidth(self, mock_post):
        """有质押带宽的账户"""
        from tron_mcp_server import call_router
        
        # Mock TronGrid /wallet/getaccountresource 响应 - 有质押带宽
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 50,
            "NetLimit": 5000,
            "NetUsed": 1000,
        }
        
        result = call_router.call("get_account_bandwidth", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["free_net_limit"], 600)
        self.assertEqual(result["net_limit"], 5000)
        self.assertEqual(result["net_remaining"], 4000)
        self.assertEqual(result["total_bandwidth"], 5600)
        self.assertEqual(result["total_remaining"], 4550)
        self.assertIn("summary", result)
        self.assertIn("质押带宽", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_bandwidth_transfer_estimate(self, mock_post):
        """带宽 summary 应包含转账估算"""
        from tron_mcp_server import call_router
        
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 0,
            "NetLimit": 2000,
            "NetUsed": 100,
        }
        
        result = call_router.call("get_account_bandwidth", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        # total_remaining = 600 + 1900 = 2500
        self.assertEqual(result["total_remaining"], 2500)
        self.assertIn("summary", result)
        self.assertIn("TRX 转账", result["summary"])
        self.assertIn("USDT 转账", result["summary"])

    @patch('tron_mcp_server.trongrid_client._post')
    def test_bandwidth_with_all_fields(self, mock_post):
        """测试所有字段都正确返回"""
        from tron_mcp_server import call_router
        
        mock_post.return_value = {
            "freeNetLimit": 600,
            "freeNetUsed": 200,
            "NetLimit": 3000,
            "NetUsed": 500,
            "TotalNetLimit": 43200000000,
            "TotalNetWeight": 84687233463517,
        }
        
        result = call_router.call("get_account_bandwidth", {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        })
        
        self.assertNotIn("error", result)
        self.assertEqual(result["free_net_limit"], 600)
        self.assertEqual(result["free_net_used"], 200)
        self.assertEqual(result["free_net_remaining"], 400)
        self.assertEqual(result["net_limit"], 3000)
        self.assertEqual(result["net_used"], 500)
        self.assertEqual(result["net_remaining"], 2500)
        self.assertEqual(result["total_bandwidth"], 3600)
        self.assertEqual(result["total_used"], 700)
        self.assertEqual(result["total_remaining"], 2900)


class TestFormatters(unittest.TestCase):
    """测试 formatters.py 中的格式化函数"""

    def test_format_account_energy_zero(self):
        """测试格式化零能量账户"""
        from tron_mcp_server import formatters
        
        result = {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "energy_limit": 0,
            "energy_used": 0,
            "energy_remaining": 0,
        }
        
        formatted = formatters.format_account_energy(result)
        self.assertIn("summary", formatted)
        self.assertIn("无能量额度", formatted["summary"])
        self.assertIn("燃烧 TRX", formatted["summary"])

    def test_format_account_energy_with_balance(self):
        """测试格式化有能量的账户"""
        from tron_mcp_server import formatters
        
        result = {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "energy_limit": 130000,
            "energy_used": 0,
            "energy_remaining": 130000,
        }
        
        formatted = formatters.format_account_energy(result)
        self.assertIn("summary", formatted)
        self.assertIn("130,000", formatted["summary"])
        self.assertIn("USDT 转账", formatted["summary"])

    def test_format_account_bandwidth_free_only(self):
        """测试格式化仅免费带宽"""
        from tron_mcp_server import formatters
        
        result = {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "free_net_limit": 600,
            "free_net_used": 100,
            "free_net_remaining": 500,
            "net_limit": 0,
            "net_used": 0,
            "net_remaining": 0,
            "total_bandwidth": 600,
            "total_used": 100,
            "total_remaining": 500,
        }
        
        formatted = formatters.format_account_bandwidth(result)
        self.assertIn("summary", formatted)
        self.assertIn("免费带宽", formatted["summary"])
        self.assertIn("500", formatted["summary"])
        self.assertIn("无（未质押", formatted["summary"])

    def test_format_account_bandwidth_with_staking(self):
        """测试格式化有质押带宽"""
        from tron_mcp_server import formatters
        
        result = {
            "address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "free_net_limit": 600,
            "free_net_used": 0,
            "free_net_remaining": 600,
            "net_limit": 10000,
            "net_used": 2000,
            "net_remaining": 8000,
            "total_bandwidth": 10600,
            "total_used": 2000,
            "total_remaining": 8600,
        }
        
        formatted = formatters.format_account_bandwidth(result)
        self.assertIn("summary", formatted)
        self.assertIn("质押带宽", formatted["summary"])
        self.assertIn("8,000", formatted["summary"])
        self.assertIn("TRX 转账", formatted["summary"])


class TestServerTools(unittest.TestCase):
    """测试 server.py 中的 MCP 工具注册"""

    def test_energy_tool_exists(self):
        """验证 tron_get_account_energy 工具已注册"""
        from tron_mcp_server import server
        
        self.assertTrue(hasattr(server, 'tron_get_account_energy'))

    def test_bandwidth_tool_exists(self):
        """验证 tron_get_account_bandwidth 工具已注册"""
        from tron_mcp_server import server
        
        self.assertTrue(hasattr(server, 'tron_get_account_bandwidth'))


if __name__ == '__main__':
    unittest.main()
