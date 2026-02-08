"""
测试 memo（备注）功能
=====================================================

测试 TRON 转账交易中的 memo 功能：
- memo 字符串到 hex 编码的转换
- TRX 转账中的 memo 参数传递
- TRC20 (USDT) 转账中的 memo 参数传递
- 空 memo 的处理
"""

import unittest
import sys
import os

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import trongrid_client, call_router


class TestMemoEncoding(unittest.TestCase):
    """测试 memo 编码"""

    def test_utf8_to_hex_encoding(self):
        """测试 UTF-8 字符串到 hex 的编码"""
        # 英文
        memo = "Invoice #1234"
        memo_hex = memo.encode("utf-8").hex()
        self.assertEqual(memo_hex, "496e766f69636520233132333" + "4")
        
        # 中文
        memo = "还你的饭钱"
        memo_hex = memo.encode("utf-8").hex()
        # 验证是有效的 hex 字符串
        self.assertTrue(all(c in "0123456789abcdef" for c in memo_hex))
        # 可以解码回原字符串
        decoded = bytes.fromhex(memo_hex).decode("utf-8")
        self.assertEqual(decoded, "还你的饭钱")
    
    def test_empty_memo(self):
        """测试空 memo"""
        memo = ""
        memo_hex = memo.encode("utf-8").hex()
        self.assertEqual(memo_hex, "")
    
    def test_special_characters(self):
        """测试特殊字符"""
        memo = "Payment: $100.50 💰"
        memo_hex = memo.encode("utf-8").hex()
        # 可以解码回原字符串
        decoded = bytes.fromhex(memo_hex).decode("utf-8")
        self.assertEqual(decoded, memo)


class TestTrxTransferWithMemo(unittest.TestCase):
    """测试 TRX 转账中的 memo"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_trx_transfer_with_memo(self, mock_post):
        """TRX 转账应正确传递 extra_data"""
        mock_post.return_value = {
            "txID": "a" * 64,
            "raw_data": {"contract": []},
            "raw_data_hex": "0000",
        }
        
        memo = "Test memo"
        memo_hex = memo.encode("utf-8").hex()
        
        result = trongrid_client.build_trx_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            10.0,
            extra_data=memo_hex,
        )
        
        # 验证调用参数包含 extra_data
        call_data = mock_post.call_args[0][1]
        self.assertIn("extra_data", call_data)
        self.assertEqual(call_data["extra_data"], memo_hex)
        
        # 验证返回结果
        self.assertIn("txID", result)
    
    @patch('tron_mcp_server.trongrid_client._post')
    def test_trx_transfer_without_memo(self, mock_post):
        """TRX 转账不带 memo 时不应包含 extra_data"""
        mock_post.return_value = {
            "txID": "b" * 64,
            "raw_data": {"contract": []},
            "raw_data_hex": "0000",
        }
        
        result = trongrid_client.build_trx_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            10.0,
        )
        
        # 验证调用参数不包含 extra_data
        call_data = mock_post.call_args[0][1]
        self.assertNotIn("extra_data", call_data)
        
        # 验证返回结果
        self.assertIn("txID", result)
    
    @patch('tron_mcp_server.trongrid_client._post')
    def test_trx_transfer_with_chinese_memo(self, mock_post):
        """TRX 转账使用中文 memo"""
        mock_post.return_value = {
            "txID": "c" * 64,
            "raw_data": {"contract": []},
            "raw_data_hex": "0000",
        }
        
        memo = "还你的饭钱"
        memo_hex = memo.encode("utf-8").hex()
        
        result = trongrid_client.build_trx_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            5.0,
            extra_data=memo_hex,
        )
        
        # 验证调用参数
        call_data = mock_post.call_args[0][1]
        self.assertEqual(call_data["extra_data"], memo_hex)


class TestTrc20TransferWithMemo(unittest.TestCase):
    """测试 TRC20 转账中的 memo"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_trc20_transfer_with_memo(self, mock_post):
        """TRC20 转账应正确传递 extra_data"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {
                "txID": "d" * 64,
                "raw_data": {"contract": []},
            },
        }
        
        memo = "USDT payment"
        memo_hex = memo.encode("utf-8").hex()
        
        result = trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            100.0,
            extra_data=memo_hex,
        )
        
        # 验证调用参数包含 extra_data
        call_data = mock_post.call_args[0][1]
        self.assertIn("extra_data", call_data)
        self.assertEqual(call_data["extra_data"], memo_hex)
        
        # 验证返回结果
        self.assertIn("txID", result)
    
    @patch('tron_mcp_server.trongrid_client._post')
    def test_trc20_transfer_without_memo(self, mock_post):
        """TRC20 转账不带 memo 时不应包含 extra_data"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": {
                "txID": "e" * 64,
                "raw_data": {"contract": []},
            },
        }
        
        result = trongrid_client.build_trc20_transfer(
            "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            50.0,
        )
        
        # 验证调用参数不包含 extra_data
        call_data = mock_post.call_args[0][1]
        self.assertNotIn("extra_data", call_data)
        
        # 验证返回结果
        self.assertIn("txID", result)


class TestCallRouterWithMemo(unittest.TestCase):
    """测试 call_router 中的 memo 处理"""

    @patch('tron_mcp_server.call_router.trongrid_client.build_trx_transfer')
    @patch('tron_mcp_server.call_router.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.call_router.validators.is_valid_address')
    @patch('tron_mcp_server.call_router.validators.is_positive_amount')
    def test_handle_build_tx_with_memo(
        self, 
        mock_is_positive, 
        mock_is_valid,
        mock_build_unsigned,
        mock_build_trx
    ):
        """测试 _handle_build_tx 处理 memo"""
        # 设置 mock
        mock_is_valid.return_value = True
        mock_is_positive.return_value = True
        mock_build_unsigned.return_value = {
            "txID": "preview123",
            "raw_data": {},
        }
        mock_build_trx.return_value = {
            "txID": "real123",
            "raw_data": {},
        }
        
        # 调用 _handle_build_tx
        params = {
            "from": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 10.0,
            "token": "TRX",
            "memo": "Test memo",
        }
        result = call_router._handle_build_tx(params)
        
        # 验证调用了 TronGrid 构建真实交易
        mock_build_trx.assert_called_once()
        call_kwargs = mock_build_trx.call_args[1]
        self.assertIn("extra_data", call_kwargs)
        
        # 验证 extra_data 是 hex 编码的 memo
        expected_hex = "Test memo".encode("utf-8").hex()
        self.assertEqual(call_kwargs["extra_data"], expected_hex)
        
        # 验证结果包含 summary 中提到 memo
        self.assertIn("summary", result)
        self.assertIn("Test memo", result["summary"])

    @patch('tron_mcp_server.call_router.trongrid_client.build_trx_transfer')
    @patch('tron_mcp_server.call_router.key_manager.load_private_key')
    @patch('tron_mcp_server.call_router.key_manager.get_address_from_private_key')
    @patch('tron_mcp_server.call_router.key_manager.sign_transaction')
    @patch('tron_mcp_server.call_router.trongrid_client.broadcast_transaction')
    @patch('tron_mcp_server.call_router.tx_builder.build_unsigned_tx')
    @patch('tron_mcp_server.call_router.validators.is_valid_address')
    @patch('tron_mcp_server.call_router.validators.is_positive_amount')
    @patch('tron_mcp_server.call_router.formatters.format_transfer_result')
    def test_handle_transfer_with_memo(
        self,
        mock_format,
        mock_is_positive,
        mock_is_valid,
        mock_build_unsigned,
        mock_broadcast,
        mock_sign,
        mock_get_addr,
        mock_load_pk,
        mock_build_trx
    ):
        """测试 _handle_transfer 处理 memo"""
        # 设置 mock
        mock_is_valid.return_value = True
        mock_is_positive.return_value = True
        mock_load_pk.return_value = "private_key"
        mock_get_addr.return_value = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        mock_build_unsigned.return_value = {
            "txID": "preview123",
            "raw_data": {},
        }
        mock_build_trx.return_value = {
            "txID": "real123",
            "raw_data": {},
        }
        mock_sign.return_value = "signature123"
        mock_broadcast.return_value = {"result": True}
        mock_format.return_value = {"txid": "real123", "result": True}
        
        # 调用 _handle_transfer
        params = {
            "to": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 5.0,
            "token": "TRX",
            "memo": "Transfer memo",
        }
        result = call_router._handle_transfer(params)
        
        # 验证调用了 TronGrid 构建交易
        mock_build_trx.assert_called_once()
        call_kwargs = mock_build_trx.call_args[1]
        self.assertIn("extra_data", call_kwargs)
        
        # 验证 extra_data 是 hex 编码的 memo
        expected_hex = "Transfer memo".encode("utf-8").hex()
        self.assertEqual(call_kwargs["extra_data"], expected_hex)


if __name__ == "__main__":
    unittest.main()
