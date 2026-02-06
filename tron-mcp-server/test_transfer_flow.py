"""
本地私钥管理 + 转账闭环 完整测试
===================================

覆盖以下模块：

1. key_manager.py — 私钥管理
   - 私钥加载（环境变量、0x 前缀、非法格式）
   - 地址派生（已知私钥 → 已知地址）
   - ECDSA secp256k1 签名（格式、长度、recovery_id）
   - 地址所有权验证

2. trongrid_client.py — TronGrid API 交互
   - 地址格式转换（Base58 ↔ Hex）
   - TRX 转账交易构建（mock API）
   - TRC20 转账交易构建（mock API）
   - 交易广播（成功 / 失败）

3. call_router.py — 转账闭环集成
   - broadcast_tx 路由（广播已签名交易）
   - transfer 路由（完整闭环）
   - get_wallet_info 路由（钱包信息）
   - 错误场景（无私钥、地址不匹配、余额不足）

注意：sign_tx 路由已在工具精简中被删除，相关测试已移除。
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

from tron_mcp_server import key_manager
from tron_mcp_server import trongrid_client
from tron_mcp_server import call_router
from tron_mcp_server import formatters

# ============================================================
# 测试常量
# ============================================================

# 已知的测试私钥 (仅用于测试, 不要在主网使用!)
# 私钥 1 → 已知地址
TEST_PRIVATE_KEY = "0000000000000000000000000000000000000000000000000000000000000001"
# 通过 secp256k1 公钥推导出的地址 (已通过运行时验证)
TEST_ADDRESS = "TMVQGm1qAQYVdetCeGRRkTWYYrLXuHK2HC"

# 第二个测试私钥
TEST_PRIVATE_KEY_2 = "0000000000000000000000000000000000000000000000000000000000000002"

# 模拟的 TronGrid 交易响应
MOCK_TRX_TX = {
    "txID": "a" * 64,
    "raw_data": {
        "contract": [{
            "parameter": {
                "value": {
                    "amount": 1000000,
                    "owner_address": "41" + "0" * 40,
                    "to_address": "41" + "1" * 40,
                },
                "type_url": "type.googleapis.com/protocol.TransferContract",
            },
            "type": "TransferContract",
        }],
        "ref_block_bytes": "abcd",
        "ref_block_hash": "1234567890abcdef",
        "expiration": 1700000000000,
        "timestamp": 1699999000000,
    },
    "raw_data_hex": "0a" * 50,
}

MOCK_TRC20_TX = {
    "txID": "b" * 64,
    "raw_data": {
        "contract": [{
            "parameter": {
                "value": {
                    "data": "a9059cbb" + "0" * 128,
                    "owner_address": "41" + "0" * 40,
                    "contract_address": "41a614f803b6fd780986a42c78ec9c7f77e6ded13c",
                },
                "type_url": "type.googleapis.com/protocol.TriggerSmartContract",
            },
            "type": "TriggerSmartContract",
        }],
        "ref_block_bytes": "abcd",
        "ref_block_hash": "1234567890abcdef",
        "expiration": 1700000000000,
        "timestamp": 1699999000000,
        "fee_limit": 100000000,
    },
    "raw_data_hex": "0b" * 50,
}


# ============================================================
# 1. key_manager 单元测试
# ============================================================

class TestKeyManagerLoadPrivateKey(unittest.TestCase):
    """测试私钥加载"""

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_load_valid_key(self):
        """正常加载 64 位十六进制私钥"""
        pk = key_manager.load_private_key()
        self.assertEqual(pk, TEST_PRIVATE_KEY)
        self.assertEqual(len(pk), 64)

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": "0x" + TEST_PRIVATE_KEY})
    def test_load_key_with_0x_prefix(self):
        """自动去除 0x 前缀"""
        pk = key_manager.load_private_key()
        self.assertEqual(pk, TEST_PRIVATE_KEY)

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_load_empty_key_raises(self):
        """未设置私钥时抛出 ValueError"""
        with self.assertRaises(ValueError) as cm:
            key_manager.load_private_key()
        self.assertIn("未配置私钥", str(cm.exception))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": "abc"})
    def test_load_short_key_raises(self):
        """私钥长度不足时抛出 ValueError"""
        with self.assertRaises(ValueError) as cm:
            key_manager.load_private_key()
        self.assertIn("长度无效", str(cm.exception))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": "g" * 64})
    def test_load_non_hex_key_raises(self):
        """私钥包含非法字符时抛出 ValueError"""
        with self.assertRaises(ValueError) as cm:
            key_manager.load_private_key()
        self.assertIn("非法字符", str(cm.exception))

    @patch.dict(os.environ, {}, clear=False)
    def test_load_unset_key_raises(self):
        """环境变量未设置时抛出 ValueError"""
        env = os.environ.copy()
        env.pop("TRON_PRIVATE_KEY", None)
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                key_manager.load_private_key()


class TestKeyManagerAddressDerivation(unittest.TestCase):
    """测试地址派生"""

    def test_known_key_to_address(self):
        """已知私钥 → 已知地址"""
        addr = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertEqual(addr, TEST_ADDRESS)

    def test_address_format(self):
        """派生地址格式：T 开头, 34 字符"""
        addr = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertTrue(addr.startswith("T"))
        self.assertEqual(len(addr), 34)

    def test_different_keys_different_addresses(self):
        """不同私钥 → 不同地址"""
        addr1 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        addr2 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY_2)
        self.assertNotEqual(addr1, addr2)

    def test_deterministic(self):
        """同一私钥多次派生 → 同一地址"""
        addr1 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        addr2 = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertEqual(addr1, addr2)

    def test_address_is_tron_not_ethereum(self):
        """确认派生出的是 TRON 地址（T 开头），而非以太坊地址（0x 开头）"""
        addr = key_manager.get_address_from_private_key(TEST_PRIVATE_KEY)
        self.assertTrue(addr.startswith("T"), f"TRON 地址应以 T 开头，实际为: {addr}")
        self.assertFalse(addr.startswith("0x"), "不应生成以太坊地址")
        # 验证 Base58Check 解码后以 0x41 开头（TRON 主网前缀）
        import base58 as _b58
        raw = _b58.b58decode_check(addr)
        self.assertEqual(raw[0], 0x41, "TRON 地址解码后应以 0x41 开头")


class TestKeyManagerSigning(unittest.TestCase):
    """测试交易签名"""

    def test_signature_length(self):
        """签名长度: 65 bytes (130 hex chars)"""
        sig = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        self.assertEqual(len(sig), 130)

    def test_signature_is_hex(self):
        """签名为纯十六进制字符串"""
        sig = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        # 验证每个字符都是合法的十六进制字符
        bytes.fromhex(sig)  # 如果不是合法 hex, 此处会抛异常

    def test_signature_deterministic(self):
        """RFC 6979 确定性签名: 同一输入 → 同一签名"""
        sig1 = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        sig2 = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        self.assertEqual(sig1, sig2)

    def test_different_txid_different_signature(self):
        """不同 txID → 不同签名"""
        sig1 = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        sig2 = key_manager.sign_transaction("b" * 64, TEST_PRIVATE_KEY)
        self.assertNotEqual(sig1, sig2)

    def test_recovery_id_valid(self):
        """recovery_id 最后一个字节应为 0 或 1"""
        sig = key_manager.sign_transaction("a" * 64, TEST_PRIVATE_KEY)
        recovery_byte = int(sig[-2:], 16)
        self.assertIn(recovery_byte, [0, 1])


class TestKeyManagerOwnership(unittest.TestCase):
    """测试地址所有权验证"""

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_verify_correct_address(self):
        """正确地址 → True"""
        self.assertTrue(key_manager.verify_address_ownership(TEST_ADDRESS))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_verify_wrong_address(self):
        """错误地址 → False"""
        self.assertFalse(key_manager.verify_address_ownership("TXxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx123"))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_verify_no_key_configured(self):
        """未配置私钥 → False"""
        self.assertFalse(key_manager.verify_address_ownership(TEST_ADDRESS))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_get_configured_address(self):
        """获取配置的钱包地址"""
        addr = key_manager.get_configured_address()
        self.assertEqual(addr, TEST_ADDRESS)


# ============================================================
# 2. trongrid_client 单元测试
# ============================================================

class TestTronGridAddressConversion(unittest.TestCase):
    """测试地址格式转换"""

    def test_base58_to_hex(self):
        """Base58 → Hex (含 41 前缀)"""
        hex_addr = trongrid_client._base58_to_hex(TEST_ADDRESS)
        self.assertTrue(hex_addr.startswith("41"))
        self.assertEqual(len(hex_addr), 42)

    def test_hex_passthrough(self):
        """41... Hex 格式直接通过"""
        hex_input = "41" + "a" * 40
        result = trongrid_client._base58_to_hex(hex_input)
        self.assertEqual(result, hex_input)

    def test_0x_hex_strip(self):
        """0x41... 格式去掉 0x"""
        hex_input = "0x41" + "a" * 40
        result = trongrid_client._base58_to_hex(hex_input)
        self.assertEqual(result, "41" + "a" * 40)

    def test_invalid_address_raises(self):
        """无效地址抛出 ValueError"""
        with self.assertRaises(ValueError):
            trongrid_client._base58_to_hex("invalid_address")


class TestTronGridBuildTRX(unittest.TestCase):
    """测试 TRX 转账交易构建"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_build_trx_transfer_success(self, mock_post):
        """成功构建 TRX 转账"""
        mock_post.return_value = MOCK_TRX_TX.copy()

        result = trongrid_client.build_trx_transfer(
            TEST_ADDRESS, TEST_ADDRESS, 1.0
        )

        self.assertIn("txID", result)
        self.assertIn("raw_data", result)
        mock_post.assert_called_once()

        # 验证 API 调用参数
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "wallet/createtransaction")
        self.assertEqual(call_args[0][1]["amount"], 1000000)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_build_trx_transfer_error(self, mock_post):
        """TronGrid 返回错误"""
        mock_post.return_value = {"Error": "Account not found"}

        with self.assertRaises(ValueError) as cm:
            trongrid_client.build_trx_transfer(TEST_ADDRESS, TEST_ADDRESS, 1.0)
        self.assertIn("Account not found", str(cm.exception))


class TestTronGridBuildTRC20(unittest.TestCase):
    """测试 TRC20 转账交易构建"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_build_trc20_transfer_success(self, mock_post):
        """成功构建 USDT 转账"""
        mock_post.return_value = {
            "result": {"result": True},
            "transaction": MOCK_TRC20_TX.copy(),
        }

        result = trongrid_client.build_trc20_transfer(
            TEST_ADDRESS, TEST_ADDRESS, 100.0
        )

        self.assertIn("txID", result)
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "wallet/triggersmartcontract")

    @patch('tron_mcp_server.trongrid_client._post')
    def test_build_trc20_transfer_error(self, mock_post):
        """TronGrid 返回 TRC20 构建错误"""
        mock_post.return_value = {
            "result": {"result": False, "message": "Contract not found"},
        }

        with self.assertRaises(ValueError) as cm:
            trongrid_client.build_trc20_transfer(TEST_ADDRESS, TEST_ADDRESS, 100.0)
        self.assertIn("失败", str(cm.exception))


class TestTronGridBroadcast(unittest.TestCase):
    """测试交易广播"""

    @patch('tron_mcp_server.trongrid_client._post')
    def test_broadcast_success(self, mock_post):
        """成功广播"""
        mock_post.return_value = {"result": True, "txid": "a" * 64}

        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {"test": True},
            "signature": ["sig_hex"],
        }
        result = trongrid_client.broadcast_transaction(signed_tx)
        self.assertTrue(result["result"])
        self.assertEqual(result["txid"], "a" * 64)

    @patch('tron_mcp_server.trongrid_client._post')
    def test_broadcast_failure(self, mock_post):
        """广播失败"""
        mock_post.return_value = {
            "result": False,
            "code": "SIGERROR",
            "message": "Signature validation failed",
        }

        signed_tx = {
            "txID": "a" * 64,
            "raw_data": {"test": True},
            "signature": ["bad_sig"],
        }
        with self.assertRaises(ValueError) as cm:
            trongrid_client.broadcast_transaction(signed_tx)
        self.assertIn("广播失败", str(cm.exception))

    def test_broadcast_missing_signature_raises(self):
        """缺少签名字段 → ValueError"""
        with self.assertRaises(ValueError) as cm:
            trongrid_client.broadcast_transaction({"txID": "a" * 64, "raw_data": {}})
        self.assertIn("signature", str(cm.exception))

    def test_broadcast_missing_txid_raises(self):
        """缺少 txID → ValueError"""
        with self.assertRaises(ValueError) as cm:
            trongrid_client.broadcast_transaction({"raw_data": {}, "signature": ["s"]})
        self.assertIn("txID", str(cm.exception))


# ============================================================
# 3. call_router 集成测试 — 转账闭环
# ============================================================

class TestCallRouterBroadcastTx(unittest.TestCase):
    """测试 broadcast_tx 路由"""

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_broadcast_success(self, mock_broadcast):
        """成功广播"""
        mock_broadcast.return_value = {"result": True, "txid": "c" * 64}

        signed_tx = {
            "txID": "c" * 64,
            "raw_data": {},
            "signature": ["sig"],
        }
        result = call_router.call("broadcast_tx", {
            "signed_tx_json": json.dumps(signed_tx),
        })

        self.assertNotIn("error", result)
        self.assertTrue(result.get("result"))
        self.assertIn("txid", result)
        self.assertIn("成功广播", result.get("summary", ""))

    def test_broadcast_invalid_json(self):
        """无效 JSON → 错误"""
        result = call_router.call("broadcast_tx", {
            "signed_tx_json": "not valid json{{{",
        })
        self.assertIn("error", result)

    def test_broadcast_missing_params(self):
        """缺少 signed_tx_json → 错误"""
        result = call_router.call("broadcast_tx", {})
        self.assertIn("error", result)

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    def test_broadcast_dict_input(self, mock_broadcast):
        """直接传入字典（非 JSON 字符串）→ 兼容处理"""
        mock_broadcast.return_value = {"result": True, "txid": "d" * 64}

        signed_tx = {
            "txID": "d" * 64,
            "raw_data": {},
            "signature": ["sig"],
        }
        result = call_router.call("broadcast_tx", {
            "signed_tx_json": signed_tx,
        })

        self.assertNotIn("error", result)
        self.assertTrue(result.get("result"))


class TestCallRouterTransfer(unittest.TestCase):
    """测试 transfer 路由 — 完整闭环"""

    @patch('tron_mcp_server.trongrid_client.broadcast_transaction')
    @patch('tron_mcp_server.trongrid_client.build_trc20_transfer')
    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_transfer_usdt_full_flow(self, mock_safety, mock_build, mock_broadcast):
        """完整 USDT 转账闭环: 安全检查 → 构建 → 签名 → 广播"""
        # 安全检查通过 (不拦截)
        mock_safety.return_value = {
            "txID": "safety_check",
            "raw_data": {},
        }
        # TronGrid 构建交易
        mock_build.return_value = MOCK_TRC20_TX.copy()
        # 广播成功
        mock_broadcast.return_value = {"result": True, "txid": MOCK_TRC20_TX["txID"]}

        result = call_router.call("transfer", {
            "to": TEST_ADDRESS,
            "amount": 10.0,
            "token": "USDT",
        })

        self.assertNotIn("error", result)
        self.assertTrue(result.get("result"))
        self.assertIn("txid", result)
        self.assertIn("转账成功", result.get("summary", ""))
        self.assertEqual(result.get("amount"), 10.0)
        self.assertEqual(result.get("token"), "USDT")

    @patch('tron_mcp_server.tx_builder.build_unsigned_tx')
    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_transfer_blocked_by_security(self, mock_safety):
        """恶意地址 → 被熔断拦截"""
        mock_safety.return_value = {
            "blocked": True,
            "summary": "🛑 交易已拦截: 接收方为恶意地址",
        }

        result = call_router.call("transfer", {
            "to": TEST_ADDRESS,
            "amount": 10.0,
            "token": "USDT",
        })

        self.assertTrue(result.get("blocked"))
        self.assertIn("拦截", result.get("summary", ""))

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_transfer_no_private_key(self):
        """未配置私钥 → 错误"""
        result = call_router.call("transfer", {
            "to": TEST_ADDRESS,
            "amount": 10.0,
        })
        self.assertIn("error", result)

    def test_transfer_missing_params(self):
        """缺少必填参数 → 错误"""
        result = call_router.call("transfer", {"amount": 10.0})
        self.assertIn("error", result)

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_transfer_invalid_address(self):
        """无效地址 → 错误"""
        result = call_router.call("transfer", {
            "to": "invalid_addr",
            "amount": 10.0,
        })
        self.assertIn("error", result)

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_transfer_zero_amount(self):
        """金额为零 → 错误"""
        result = call_router.call("transfer", {
            "to": TEST_ADDRESS,
            "amount": 0,
        })
        self.assertIn("error", result)


class TestCallRouterGetWalletInfo(unittest.TestCase):
    """测试 get_wallet_info 路由"""

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_wallet_info_success(self, mock_trx, mock_usdt):
        """成功获取钱包信息"""
        mock_trx.return_value = 123.456
        mock_usdt.return_value = 789.012

        result = call_router.call("get_wallet_info", {})

        self.assertNotIn("error", result)
        self.assertEqual(result["address"], TEST_ADDRESS)
        self.assertEqual(result["trx_balance"], 123.456)
        self.assertEqual(result["usdt_balance"], 789.012)
        self.assertIn(TEST_ADDRESS, result["summary"])

    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": ""})
    def test_wallet_info_no_key(self):
        """未配置私钥 → 错误"""
        result = call_router.call("get_wallet_info", {})
        self.assertIn("error", result)

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_wallet_info_api_failure_graceful(self, mock_trx, mock_usdt):
        """API 查询失败时优雅降级（余额显示 0）"""
        mock_trx.side_effect = Exception("Network error")
        mock_usdt.side_effect = Exception("Timeout")

        result = call_router.call("get_wallet_info", {})

        self.assertNotIn("error", result)
        self.assertEqual(result["address"], TEST_ADDRESS)
        self.assertEqual(result["trx_balance"], 0.0)
        self.assertEqual(result["usdt_balance"], 0.0)


# ============================================================
# 4. formatters 单元测试
# ============================================================

class TestFormatters(unittest.TestCase):
    """测试新增的格式化函数"""

    def test_format_signed_tx(self):
        """签名交易格式化"""
        signed_tx = {"txID": "abc123", "signature": ["sig"]}
        result = formatters.format_signed_tx(
            signed_tx, "Tfrom", "Tto", 100.0, "USDT"
        )
        self.assertIn("signed_tx", result)
        self.assertIn("signed_tx_json", result)
        self.assertIn("txID", result)
        self.assertIn("broadcast", result["summary"].lower())

    def test_format_broadcast_result(self):
        """广播结果格式化"""
        result = formatters.format_broadcast_result(
            {"result": True, "txid": "d" * 64}
        )
        self.assertTrue(result["result"])
        self.assertIn("成功广播", result["summary"])
        self.assertIn("d" * 64, result["txid"])

    def test_format_transfer_result(self):
        """转账结果格式化"""
        result = formatters.format_transfer_result(
            {"result": True, "txid": "e" * 64},
            "Tfrom123", "Tto456", 50.5, "TRX",
        )
        self.assertTrue(result["result"])
        self.assertEqual(result["amount"], 50.5)
        self.assertEqual(result["token"], "TRX")
        self.assertIn("转账成功", result["summary"])

    def test_format_wallet_info(self):
        """钱包信息格式化"""
        result = formatters.format_wallet_info(
            TEST_ADDRESS, 100.5, 200.3
        )
        self.assertEqual(result["address"], TEST_ADDRESS)
        self.assertEqual(result["trx_balance"], 100.5)
        self.assertEqual(result["usdt_balance"], 200.3)
        self.assertIn(TEST_ADDRESS, result["summary"])
        self.assertIn("TRX", result["summary"])
        self.assertIn("USDT", result["summary"])


# ============================================================
# 5. 安全性测试
# ============================================================

class TestSecurityProperties(unittest.TestCase):
    """测试安全性相关属性"""

    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch.dict(os.environ, {"TRON_PRIVATE_KEY": TEST_PRIVATE_KEY})
    def test_wallet_info_no_private_key_exposed(self, mock_trx, mock_usdt):
        """钱包信息不暴露私钥"""
        mock_trx.return_value = 100.0
        mock_usdt.return_value = 200.0

        result = call_router.call("get_wallet_info", {})
        result_str = json.dumps(result)
        self.assertNotIn(TEST_PRIVATE_KEY, result_str)
        self.assertNotIn("private", result_str.lower())


# ============================================================
# main
# ============================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
