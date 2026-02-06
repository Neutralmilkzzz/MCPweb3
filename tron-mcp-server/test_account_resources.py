"""测试账户资源查询功能 (get_account_resources)"""

import unittest
import sys
import os
from unittest.mock import patch, MagicMock

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

from tron_mcp_server import call_router, formatters, trongrid_client


class TestGetAccountResourcesCallRouter(unittest.TestCase):
    """测试 call_router 中的 get_account_resources 动作"""

    def test_missing_address_returns_error(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("get_account_resources", {})
        self.assertIn("error", result)
        self.assertIn("address", result.get("summary", "").lower())

    def test_invalid_address_returns_error(self):
        """无效地址格式应返回错误"""
        result = call_router.call("get_account_resources", {
            "address": "invalid_address_123"
        })
        self.assertIn("error", result)
        self.assertIn("invalid", result.get("summary", "").lower())

    @patch('tron_mcp_server.trongrid_client.get_account_resources')
    def test_successful_query(self, mock_get_resources):
        """正常查询成功应返回格式化结果"""
        # Mock TronGrid API 返回
        mock_get_resources.return_value = {
            "freeNetUsed": 250,
            "freeNetLimit": 600,
            "NetUsed": 100,
            "NetLimit": 5243,
            "EnergyUsed": 1000,
            "EnergyLimit": 65000,
            "TotalNetLimit": 43200000000,
            "TotalNetWeight": 84687233463517,
            "TotalEnergyLimit": 90000000000,
            "TotalEnergyWeight": 13369831825062,
            "tronPowerUsed": 0,
            "tronPowerLimit": 1000,
        }

        result = call_router.call("get_account_resources", {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        })

        # 验证 Mock 被调用
        self.assertTrue(mock_get_resources.called)
        
        # 验证结果结构
        self.assertIn("address", result)
        self.assertIn("energy", result)
        self.assertIn("bandwidth", result)
        self.assertIn("tron_power", result)
        self.assertIn("network", result)
        self.assertIn("summary", result)
        
        # 验证 energy 字段
        self.assertEqual(result["energy"]["used"], 1000)
        self.assertEqual(result["energy"]["limit"], 65000)
        self.assertEqual(result["energy"]["remaining"], 64000)
        
        # 验证 bandwidth 字段
        self.assertEqual(result["bandwidth"]["free_used"], 250)
        self.assertEqual(result["bandwidth"]["free_limit"], 600)
        self.assertEqual(result["bandwidth"]["free_remaining"], 350)
        self.assertEqual(result["bandwidth"]["staked_used"], 100)
        self.assertEqual(result["bandwidth"]["staked_limit"], 5243)
        self.assertEqual(result["bandwidth"]["staked_remaining"], 5143)

    @patch('tron_mcp_server.trongrid_client.get_account_resources')
    def test_trongrid_api_error(self, mock_get_resources):
        """TronGrid API 异常应返回错误"""
        mock_get_resources.side_effect = ValueError("TronGrid 查询资源失败: INVALID_ADDRESS")

        result = call_router.call("get_account_resources", {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        })

        self.assertIn("error", result)
        self.assertIn("TronGrid", result.get("summary", ""))


class TestFormatAccountResources(unittest.TestCase):
    """测试 format_account_resources 函数"""

    def test_basic_formatting(self):
        """测试基本资源格式化"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "freeNetUsed": 250,
            "freeNetLimit": 600,
            "NetUsed": 100,
            "NetLimit": 5243,
            "EnergyUsed": 1000,
            "EnergyLimit": 65000,
            "TotalNetLimit": 43200000000,
            "TotalNetWeight": 84687233463517,
            "TotalEnergyLimit": 90000000000,
            "TotalEnergyWeight": 13369831825062,
            "tronPowerUsed": 0,
            "tronPowerLimit": 1000,
        }

        result = formatters.format_account_resources(address, resources)

        # 验证地址
        self.assertEqual(result["address"], address)
        
        # 验证 energy
        self.assertEqual(result["energy"]["used"], 1000)
        self.assertEqual(result["energy"]["limit"], 65000)
        self.assertEqual(result["energy"]["remaining"], 64000)
        
        # 验证 bandwidth
        self.assertEqual(result["bandwidth"]["free_used"], 250)
        self.assertEqual(result["bandwidth"]["free_limit"], 600)
        self.assertEqual(result["bandwidth"]["free_remaining"], 350)
        self.assertEqual(result["bandwidth"]["staked_used"], 100)
        self.assertEqual(result["bandwidth"]["staked_limit"], 5243)
        self.assertEqual(result["bandwidth"]["staked_remaining"], 5143)
        
        # 验证 tron_power
        self.assertEqual(result["tron_power"]["used"], 0)
        self.assertEqual(result["tron_power"]["limit"], 1000)
        
        # 验证 network
        self.assertEqual(result["network"]["total_energy_limit"], 90000000000)
        self.assertEqual(result["network"]["total_energy_weight"], 13369831825062)
        self.assertEqual(result["network"]["total_net_limit"], 43200000000)
        self.assertEqual(result["network"]["total_net_weight"], 84687233463517)
        
        # 验证 summary 存在
        self.assertIn("summary", result)
        self.assertIn("Energy", result["summary"])
        self.assertIn("带宽", result["summary"])

    def test_energy_remaining_calculation(self):
        """测试 energy_remaining 计算正确"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "EnergyUsed": 31000,
            "EnergyLimit": 65000,
        }

        result = formatters.format_account_resources(address, resources)
        
        # 验证剩余量计算
        self.assertEqual(result["energy"]["remaining"], 34000)  # 65000 - 31000

    def test_free_net_remaining_calculation(self):
        """测试 free_net_remaining 计算正确"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "freeNetUsed": 400,
            "freeNetLimit": 600,
        }

        result = formatters.format_account_resources(address, resources)
        
        # 验证免费带宽剩余量
        self.assertEqual(result["bandwidth"]["free_remaining"], 200)  # 600 - 400

    def test_zero_energy_limit_includes_tip(self):
        """energy_limit 为 0 时 summary 应包含提示"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "EnergyUsed": 0,
            "EnergyLimit": 0,
        }

        result = formatters.format_account_resources(address, resources)
        
        # 验证 summary 包含质押建议
        self.assertIn("提示", result["summary"])
        self.assertIn("Energy", result["summary"])
        self.assertIn("质押", result["summary"])

    def test_non_zero_energy_limit_no_tip(self):
        """energy_limit 不为 0 时 summary 不应包含提示"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "EnergyUsed": 1000,
            "EnergyLimit": 65000,
        }

        result = formatters.format_account_resources(address, resources)
        
        # 验证 summary 不包含提示
        self.assertNotIn("提示", result["summary"])

    def test_default_values_for_missing_fields(self):
        """缺失字段应使用默认值"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {}  # 空响应

        result = formatters.format_account_resources(address, resources)
        
        # 验证默认值
        self.assertEqual(result["energy"]["used"], 0)
        self.assertEqual(result["energy"]["limit"], 0)
        self.assertEqual(result["bandwidth"]["free_limit"], 600)  # 默认免费额度
        self.assertEqual(result["network"]["total_energy_limit"], 90000000000)
        self.assertEqual(result["network"]["total_net_limit"], 43200000000)

    def test_negative_remaining_clamped_to_zero(self):
        """剩余量为负数时应被限制为 0"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        resources = {
            "EnergyUsed": 70000,
            "EnergyLimit": 65000,  # used > limit
        }

        result = formatters.format_account_resources(address, resources)
        
        # 验证剩余量被限制为 0
        self.assertEqual(result["energy"]["remaining"], 0)


class TestTrongridClientGetAccountResources(unittest.TestCase):
    """测试 trongrid_client.get_account_resources 函数"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_successful_api_call(self, mock_post):
        """测试成功的 API 调用"""
        mock_post.return_value = {
            "freeNetUsed": 250,
            "freeNetLimit": 600,
            "EnergyLimit": 65000,
        }

        result = trongrid_client.get_account_resources("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")

        # 验证 _post 被正确调用
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "wallet/getaccountresource")
        
        # 验证请求参数
        request_data = call_args[0][1]
        self.assertIn("address", request_data)
        self.assertEqual(request_data["visible"], False)
        
        # 验证返回结果
        self.assertEqual(result["freeNetUsed"], 250)
        self.assertEqual(result["freeNetLimit"], 600)
        self.assertEqual(result["EnergyLimit"], 65000)

    @patch('tron_mcp_server.trongrid_client._base58_to_hex')
    @patch('tron_mcp_server.trongrid_client._post')
    def test_api_error_response(self, mock_post, mock_base58_to_hex):
        """测试 API 返回错误"""
        mock_base58_to_hex.return_value = "41a614f803b6fd780986a42c78ec9c7f77e6ded13c"
        mock_post.return_value = {
            "Error": "INVALID_ADDRESS"
        }

        with self.assertRaises(ValueError) as context:
            trongrid_client.get_account_resources("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        self.assertIn("TronGrid 查询资源失败", str(context.exception))
        self.assertIn("INVALID_ADDRESS", str(context.exception))

    @patch('tron_mcp_server.trongrid_client._base58_to_hex')
    @patch('tron_mcp_server.trongrid_client._post')
    def test_address_conversion(self, mock_post, mock_base58_to_hex):
        """测试地址转换为 hex 格式"""
        mock_base58_to_hex.return_value = "41a614f803b6fd780986a42c78ec9c7f77e6ded13c"
        mock_post.return_value = {"EnergyLimit": 65000}

        trongrid_client.get_account_resources("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")

        # 验证地址转换函数被调用
        self.assertTrue(mock_base58_to_hex.called)
        self.assertEqual(mock_base58_to_hex.call_args[0][0], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")


if __name__ == "__main__":
    unittest.main()
