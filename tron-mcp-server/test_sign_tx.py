"""
测试 tron_sign_tx MCP 工具
=========================

覆盖签名流程的各种场景：
- 参数校验（缺失、格式错误）
- 私钥配置检查
- 签名成功场景
- 签名结果格式验证
- 与广播的集成测试
"""

import unittest
from unittest.mock import patch, MagicMock
import sys
import os
import json

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


class TestSignTxHandler(unittest.TestCase):
    """测试 call_router._handle_sign_tx"""

    def test_missing_unsigned_tx_json_param(self):
        """缺少 unsigned_tx_json 参数时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("sign_tx", {})
        self.assertIn("error", result)
        self.assertIn("unsigned_tx_json", result.get("summary", ""))

    def test_invalid_json_format(self):
        """无效 JSON 格式时返回错误"""
        from tron_mcp_server import call_router
        
        result = call_router.call("sign_tx", {
            "unsigned_tx_json": "not a valid json"
        })
        self.assertIn("error", result)
        self.assertIn("JSON", result.get("summary", "").upper())

    def test_missing_txid_field(self):
        """交易缺少 txID 字段时返回错误"""
        from tron_mcp_server import call_router
        
        unsigned_tx = {
            "raw_data": {"contract": []},
            # 缺少 txID
        }
        result = call_router.call("sign_tx", {
            "unsigned_tx_json": json.dumps(unsigned_tx)
        })
        self.assertIn("error", result)
        self.assertIn("txID", result.get("summary", ""))

    def test_missing_raw_data_field(self):
        """交易缺少 raw_data 字段时返回错误"""
        from tron_mcp_server import call_router
        
        unsigned_tx = {
            "txID": "a" * 64,
            # 缺少 raw_data
        }
        result = call_router.call("sign_tx", {
            "unsigned_tx_json": json.dumps(unsigned_tx)
        })
        self.assertIn("error", result)
        self.assertIn("raw_data", result.get("summary", ""))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_missing_private_key(self):
        """未配置私钥时返回错误"""
        from tron_mcp_server import call_router
        
        unsigned_tx = {
            "txID": "a" * 64,
            "raw_data": {"contract": []},
        }
        result = call_router.call("sign_tx", {
            "unsigned_tx_json": json.dumps(unsigned_tx)
        })
        self.assertIn("error", result)
        self.assertIn("私钥", result.get("summary", ""))

    def test_successful_signing(self):
        """正常签名成功场景"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()
        
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server import call_router
            
            unsigned_tx = {
                "txID": "b" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "1234"},
            }
            result = call_router.call("sign_tx", {
                "unsigned_tx_json": json.dumps(unsigned_tx)
            })
            
            # 检查返回结果
            self.assertNotIn("error", result)
            self.assertIn("signed_tx", result)
            self.assertIn("signed_tx_json", result)
            self.assertIn("txID", result)
            self.assertIn("summary", result)
            
            # 验证 txID
            self.assertEqual(result["txID"], "b" * 64)

    def test_signature_format(self):
        """签名结果包含 signature 字段且为 130 个 hex 字符（65 bytes）"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()
        
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server import call_router
            
            unsigned_tx = {
                "txID": "c" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "5678"},
            }
            result = call_router.call("sign_tx", {
                "unsigned_tx_json": json.dumps(unsigned_tx)
            })
            
            signed_tx = result.get("signed_tx", {})
            self.assertIn("signature", signed_tx)
            self.assertIsInstance(signed_tx["signature"], list)
            self.assertEqual(len(signed_tx["signature"]), 1)
            
            # 签名应为 130 个 hex 字符（65 bytes）
            signature = signed_tx["signature"][0]
            self.assertEqual(len(signature), 130, f"签名长度应为 130，实际: {len(signature)}")
            self.assertTrue(all(c in '0123456789abcdef' for c in signature))

    def test_signed_tx_json_field(self):
        """签名结果包含 signed_tx_json 字段（JSON 字符串）"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()
        
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server import call_router
            
            unsigned_tx = {
                "txID": "d" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "9abc"},
            }
            result = call_router.call("sign_tx", {
                "unsigned_tx_json": json.dumps(unsigned_tx)
            })
            
            self.assertIn("signed_tx_json", result)
            
            # 验证可以解析为 JSON
            signed_tx_json = result["signed_tx_json"]
            parsed = json.loads(signed_tx_json)
            self.assertIn("txID", parsed)
            self.assertIn("signature", parsed)

    def test_dict_input_support(self):
        """支持 dict 类型输入（不仅仅是 JSON 字符串）"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()
        
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server import call_router
            
            unsigned_tx = {
                "txID": "e" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "def0"},
            }
            # 直接传入 dict 而不是 JSON 字符串
            result = call_router.call("sign_tx", {
                "unsigned_tx_json": unsigned_tx
            })
            
            self.assertNotIn("error", result)
            self.assertIn("signed_tx", result)
            self.assertEqual(result["txID"], "e" * 64)

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_sign_broadcast_integration(self, mock_broadcast):
        """签名 → 广播集成测试（mock broadcast）"""
        from tronpy.keys import PrivateKey
        pk = PrivateKey.random()
        hex_key = pk.hex()
        
        # Mock 广播成功
        mock_broadcast.return_value = {
            "result": True,
            "txid": "f" * 64,
        }
        
        with patch.dict(os.environ, {"TRON_PRIVATE_KEY": hex_key}):
            from tron_mcp_server import call_router
            
            # 1. 签名
            unsigned_tx = {
                "txID": "f" * 64,
                "raw_data": {"contract": [], "ref_block_bytes": "1111"},
            }
            sign_result = call_router.call("sign_tx", {
                "unsigned_tx_json": json.dumps(unsigned_tx)
            })
            
            self.assertNotIn("error", sign_result)
            signed_tx_json = sign_result["signed_tx_json"]
            
            # 2. 广播
            broadcast_result = call_router.call("broadcast_tx", {
                "signed_tx_json": signed_tx_json
            })
            
            self.assertNotIn("error", broadcast_result)
            self.assertTrue(broadcast_result.get("result"))
            self.assertEqual(broadcast_result.get("txid"), "f" * 64)


class TestSignTxTool(unittest.TestCase):
    """测试 server.py 中的 tron_sign_tx MCP 工具"""

    def test_tool_exists(self):
        """验证 tron_sign_tx 工具已注册"""
        from tron_mcp_server import server
        
        # 验证 mcp 对象有 tron_sign_tx 函数
        self.assertTrue(hasattr(server, 'tron_sign_tx'))


if __name__ == '__main__':
    unittest.main()
