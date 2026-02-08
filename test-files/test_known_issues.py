"""
针对已知问题的单元测试与集成测试
=================================

覆盖以下四大类问题：

1. 风险检测模块 (tron_client.py)
   - 信誉案底查杀缺失 (Reputation Gap): redTag 为空但 greyTag/publicTag 有 Suspicious 的地址应被检出
   - API 频率限制 (Rate Limiting): API 失败时不应默认返回"安全"，应返回"无法检测"
   - 异常捕获过于宽泛: 网络断开/代码异常不应静默返回"安全"

2. 服务器交互逻辑 (server.py / call_router.py)
   - 变量作用域安全: 所有风险变量在函数顶部有初始值
   - 熔断机制严密性: force_execution=True 时才放行风险交易
   - 拦截信息可解析性: LLM 能理解拦截返回的结构

3. 交易构建模块 (tx_builder.py)
   - 手续费估算误差: 免费 600 带宽未动态抵扣
   - 边界余额用户: 余额刚够 13 TRX 时不应误报不足

4. 架构与工程化
   - 缺乏交易状态回执: 广播后无法查询链上确认
   - 异常捕获过于宽泛: except Exception 默认返回安全是危险的
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import sys
import os
import json

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
from tron_mcp_server.tx_builder import (
    check_sender_balance,
    check_recipient_status,
    check_recipient_security,
    build_unsigned_tx,
    InsufficientBalanceError,
    ESTIMATED_USDT_ENERGY,
    ENERGY_PRICE_SUN,
    SUN_PER_TRX,
)
from tron_mcp_server import call_router
from tron_mcp_server import formatters

import asyncio
import time

class TestSystemPerformance(unittest.IsolatedAsyncioTestCase):
    """
    系统压力测试与高并发稳定性
    """

    # 修正点：将 get_account_v2 改为 get_account_status 或 _get_account
    # 考虑到 call_router 内部通常调用公有接口，这里改为 get_account_status
    @patch('tron_mcp_server.tron_client.get_account_status')
    @patch('tron_mcp_server.tron_client.check_account_risk')
    async def test_concurrent_routing_stress(self, mock_risk, mock_account):
        """
        高并发场景下的路由与格式化压力测试
        """
        # 匹配 get_account_status 的返回结构
        mock_account.return_value = {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "is_activated": True,
            "has_trx": True,
            "trx_balance": 1000.0,
            "total_transactions": 500
        }
        mock_risk.return_value = {
            "is_risky": False,
            "risk_type": "Safe",
            "tags": {"Blue": "Binance"},
            "is_safe": True # 确保包含此字段供断言使用
        }

        concurrent_tasks = 50
        start_time = time.perf_counter()

        async def run_router_call(i):
            # 确保你的 call_router.call 内部逻辑会触发上述 Mock
            return call_router.call("check_account_safety", {
                "address": f"TAddress_{i}"
            })

        tasks = [run_router_call(i) for i in range(concurrent_tasks)]
        results = await asyncio.gather(*tasks)

        end_time = time.perf_counter()
        duration = end_time - start_time
        tps = concurrent_tasks / duration

        print(f"\n[STRESS TEST] 并发请求数: {concurrent_tasks}, 总耗时: {duration:.4f}s, TPS: {tps:.2f}")
        
        # 性能断言：逻辑处理应非常快
        self.assertLess(duration, 1.0, "并发路由处理速度过慢")
        self.assertEqual(len(results), concurrent_tasks)
        
# ============================================================================
# 第一部分：风险检测模块 (tron_client.py) 的单元测试
# ============================================================================

class TestReputationGap(unittest.TestCase):
    """
    问题1: 信誉案底查杀缺失 (Reputation Gap)
    
    场景: 地址没有 redTag，但 greyTag 或 publicTag 包含 Suspicious。
    预期: is_risky 应为 True，而非 False。
    
    这是最关键的 False Negative 风险：评委给出一个"有案底但没红标"的地址，
    AI 报安全 —— 这在演示中是致命的。
    """

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_grey_tag_suspicious_detected(self, mock_get):
        """greyTag 带 Suspicious 的地址应被标记为有风险"""
        # 模拟 accountv2 返回：无 redTag，但有 greyTag
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "Suspicious Activity",
            "blueTag": "",
            "publicTag": "",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        # 模拟 security API 返回：正常
        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "greyTag='Suspicious Activity' 应标记为有风险")
        self.assertTrue(any("灰度存疑" in r for r in result["risk_reasons"]))

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_public_tag_suspicious_detected(self, mock_get):
        """publicTag 包含 suspicious 关键词的地址应被标记有风险"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "",
            "blueTag": "",
            "publicTag": "Suspicious account flagged 2023",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "publicTag 包含 'suspicious' 应标记为有风险")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_public_tag_hack_detected(self, mock_get):
        """publicTag 包含 hack 关键词的地址应被标记有风险"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "",
            "blueTag": "",
            "publicTag": "Hack victim wallet",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "publicTag 包含 'hack' 应标记为有风险")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_feedback_risk_detected(self, mock_get):
        """feedbackRisk=True 的地址应被标记为有风险（用户投诉）"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "",
            "blueTag": "",
            "publicTag": "",
            "feedbackRisk": True,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "feedbackRisk=True 应标记为有风险")
        self.assertTrue(any("用户投诉" in r for r in result["risk_reasons"]))

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_fraud_transaction_history_detected(self, mock_get):
        """has_fraud_transaction=True 的地址应被标记为有风险"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "",
            "blueTag": "",
            "publicTag": "",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": True,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "has_fraud_transaction=True 应标记为有风险")
        self.assertTrue(any("欺诈交易" in r for r in result["risk_reasons"]))

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_clean_address_is_safe(self, mock_get):
        """所有标签为空、所有指标为 False 的地址应为安全"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "",
            "greyTag": "",
            "blueTag": "Binance",
            "publicTag": "",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": False,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertFalse(result["is_risky"], "干净地址应返回 is_risky=False")
        self.assertEqual(result["risk_type"], "Safe")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_multiple_risk_indicators(self, mock_get):
        """多个风险指标同时存在时，risk_reasons 应包含所有原因"""
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "Scam",
            "greyTag": "Under Investigation",
            "blueTag": "",
            "publicTag": "",
            "feedbackRisk": True,
        }
        resp_v2.status_code = 200

        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": True,
            "has_fraud_transaction": True,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"])
        # 至少应有 redTag + greyTag + feedbackRisk + blacklist + fraud = 5 条
        self.assertGreaterEqual(len(result["risk_reasons"]), 4,
                                "多风险指标应全部被记录到 risk_reasons")


class TestAPIFailureSafety(unittest.TestCase):
    """
    问题2: API 频率限制 / 异常捕获过于宽泛
    
    当前问题: API 请求失败时 (429, 403, 网络断开, 代码 bug)，
    代码通过 except Exception 默认返回 is_risky=False（安全），
    这在金融安全工具中是极其危险的"静默失效"。
    
    这些测试验证当前行为，并标注哪些是需要改进的地方。
    """

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_both_apis_fail_should_not_claim_safe(self, mock_get):
        """
        当两个安全 API 都失败时，不应声称地址安全。
        
        修复后行为: 返回 risk_type="Unknown"，并在 risk_reasons 中添加降级提示。
        """
        mock_get.side_effect = Exception("Connection refused")

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        
        # 修复后: 双 API 失败时应返回 Unknown
        self.assertEqual(result["risk_type"], "Unknown",
                         "双 API 失败时应返回 risk_type='Unknown'")
        # risk_reasons 应包含降级提示
        self.assertTrue(any("安全检查服务不可用" in r for r in result["risk_reasons"]),
                        "应包含安全检查服务不可用的提示")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_accountv2_fail_security_ok(self, mock_get):
        """accountv2 API 失败但 security API 正常，应仍能检测安全指标"""
        # 第一个请求 (accountv2) 失败
        resp_v2_fail = MagicMock()
        resp_v2_fail.json.side_effect = Exception("429 Too Many Requests")

        # 第二个请求 (security) 正常，且标记为黑名单
        resp_sec = MagicMock()
        resp_sec.json.return_value = {
            "is_black_list": True,
            "has_fraud_transaction": False,
            "fraud_token_creator": False,
            "send_ad_by_memo": False,
        }
        resp_sec.status_code = 200

        mock_get.side_effect = [resp_v2_fail, resp_sec]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "security API 检测到黑名单应报风险")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_security_api_fail_accountv2_ok(self, mock_get):
        """security API 失败但 accountv2 正常，应仍能检测标签"""
        # 第一个请求 (accountv2) 正常，有 redTag
        resp_v2 = MagicMock()
        resp_v2.json.return_value = {
            "redTag": "Phishing",
            "greyTag": "",
            "blueTag": "",
            "publicTag": "",
            "feedbackRisk": False,
        }
        resp_v2.status_code = 200

        # 第二个请求 (security) 失败
        resp_sec_fail = MagicMock()
        resp_sec_fail.json.side_effect = Exception("Network Error")

        mock_get.side_effect = [resp_v2, resp_sec_fail]

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        self.assertTrue(result["is_risky"], "accountv2 检测到 redTag 应报风险")
        self.assertEqual(result["risk_type"], "Phishing")

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_api_returns_429_rate_limit(self, mock_get):
        """模拟 API 返回 429 频率限制"""
        import httpx
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.side_effect = Exception("429 Rate Limited")
        mock_get.side_effect = Exception("429 Rate Limited")

        result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        # 修复后: 双 API 失败时应返回 Unknown 而非 Safe
        self.assertEqual(result["risk_type"], "Unknown",
                         "429 频率限制导致双 API 失败时应返回 Unknown")


class TestVariableInitialization(unittest.TestCase):
    """
    问题3: 变量定义作用域错误 (UnboundLocalError 风险)
    
    验证 check_account_risk 函数中所有风险变量在函数顶部有初始值，
    确保不会因为 API 调用失败跳过赋值而导致 UnboundLocalError。
    """

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_all_variables_initialized_when_v2_fails(self, mock_get):
        """accountv2 API 失败时，所有标签变量应有默认值，不应抛出 UnboundLocalError"""
        # accountv2 失败
        mock_get.side_effect = [
            Exception("Connection refused"),  # accountv2
            MagicMock(json=MagicMock(return_value={  # security
                "is_black_list": False,
                "has_fraud_transaction": False,
                "fraud_token_creator": False,
                "send_ad_by_memo": False,
            })),
        ]

        # 不应抛出 UnboundLocalError
        try:
            result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        except UnboundLocalError as e:
            self.fail(f"UnboundLocalError 被抛出: {e}（变量初始化缺失！）")

        # 验证返回结构完整
        self.assertIn("is_risky", result)
        self.assertIn("risk_reasons", result)
        self.assertIn("tags", result)
        self.assertIn("raw_info", result)

    @patch('tron_mcp_server.tron_client.httpx.get')
    def test_all_variables_initialized_when_both_fail(self, mock_get):
        """两个 API 都失败时，不应抛出 UnboundLocalError"""
        mock_get.side_effect = Exception("Network down")

        try:
            result = tron_client.check_account_risk("TFakeAddr1234567890123456789012345")
        except UnboundLocalError as e:
            self.fail(f"UnboundLocalError: {e}")

        # 验证 raw_info 包含所有期望字段
        self.assertIn("redTag:[]", result["raw_info"])
        self.assertIn("greyTag:[]", result["raw_info"])
        self.assertIn("is_black_list:[False]", result["raw_info"])        # 修复后: 双 API 失败应返回 Unknown
        self.assertEqual(result["risk_type"], "Unknown")

# ============================================================================
# 第二部分：服务器交互逻辑 (call_router.py) 的集成测试
# ============================================================================

class TestCircuitBreakerLogic(unittest.TestCase):
    """
    问题4: 熔断机制的严密性
    
    验证 force_execution 参数的完整工作流：
    - 有风险 + force_execution=False → 交易被拦截
    - 有风险 + force_execution=True  → 交易被构建（用户强制）
    - 无风险 + force_execution=False → 交易正常构建
    """

    @patch('tron_mcp_server.tx_builder.check_recipient_status')
    @patch('tron_mcp_server.tx_builder.check_sender_balance')
    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_risky_address_blocked_by_default(self, mock_block, mock_risk, mock_sec, mock_sender, mock_recipient):
        """风险地址 + force_execution=False → 交易被拦截"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "risk_reasons": ["🔴 高危标签 (RedTag): Scam"],
        }
        mock_sec.return_value = {
            "checked": True,
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "security_warning": "⛔ 严重安全警告",
        }

        from_addr = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        to_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        result = build_unsigned_tx(from_addr, to_addr, 10.0, "USDT", force_execution=False)
        self.assertTrue(result.get("blocked"), "风险地址应被拦截")
        self.assertIn("拦截", result.get("summary", ""), "返回信息应包含拦截说明")
        self.assertIn("force_execution", result.get("summary", ""), 
                       "拦截信息应告知用户如何强制执行")

    @patch('tron_mcp_server.tx_builder.check_recipient_status')
    @patch('tron_mcp_server.tx_builder.check_sender_balance')
    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    @patch('tron_mcp_server.tron_client.check_account_risk')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_risky_address_allowed_with_force(self, mock_block, mock_risk, mock_sec, mock_sender, mock_recipient):
        """风险地址 + force_execution=True → 交易被构建（用户强制）"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "risk_reasons": ["🔴 高危标签 (RedTag): Scam"],
        }
        mock_sec.return_value = {
            "checked": True,
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "security_warning": "⛔ 严重安全警告",
        }
        mock_sender.return_value = {"sufficient": True, "balances": {"trx": 100}}
        mock_recipient.return_value = {"warnings": [], "warning_message": None}
        mock_block.return_value = {"number": 1234567, "hash": "0" * 64}

        from_addr = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        to_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        result = build_unsigned_tx(from_addr, to_addr, 10.0, "USDT", force_execution=True)
        self.assertFalse(result.get("blocked", False), "force_execution=True 应允许交易构建")
        self.assertIn("txID", result, "应返回完整的未签名交易")

    @patch('tron_mcp_server.tx_builder.check_recipient_status')
    @patch('tron_mcp_server.tx_builder.check_sender_balance')
    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    def test_safe_address_builds_normally(self, mock_block, mock_sec, mock_sender, mock_recipient):
        """安全地址 + force_execution=False → 交易正常构建"""
        mock_sec.return_value = {
            "checked": True,
            "is_risky": False,
            "risk_type": "Safe",
            "detail": "Passed all checks",
            "security_warning": None,
        }
        mock_sender.return_value = {"sufficient": True, "balances": {"trx": 100}}
        mock_recipient.return_value = {"warnings": [], "warning_message": None}
        mock_block.return_value = {"number": 1234567, "hash": "0" * 64}

        from_addr = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        to_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        result = build_unsigned_tx(from_addr, to_addr, 10.0, "USDT")
        self.assertFalse(result.get("blocked", False))
        self.assertIn("txID", result)


class TestBlockedResponseParsability(unittest.TestCase):
    """
    问题5: 拦截信息的可解析性
    
    验证当交易被拦截时，返回的结构体包含足够信息让 LLM 理解：
    1. 这是一个拦截（blocked=True）
    2. 风险原因清晰
    3. 明确告知用户如何强制执行
    """

    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_blocked_response_structure(self, mock_risk, mock_sec):
        """拦截响应应包含 blocked, summary, risk_reasons, security_check"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "risk_reasons": ["🔴 高危标签 (RedTag): Scam"],
        }
        mock_sec.return_value = {
            "checked": True,
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "security_warning": "⛔ 严重安全警告",
        }

        from_addr = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        to_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        result = build_unsigned_tx(from_addr, to_addr, 10.0, "USDT", force_execution=False)

        # 结构完整性验证
        self.assertIn("blocked", result, "拦截响应必须包含 blocked 字段")
        self.assertTrue(result["blocked"])
        self.assertIn("summary", result, "拦截响应必须包含 summary 字段")
        self.assertIn("risk_reasons", result, "拦截响应必须包含 risk_reasons 字段")
        self.assertIn("security_check", result, "拦截响应必须包含 security_check 字段")

        # 提示信息应让 LLM 理解如何强制执行
        self.assertIn("force_execution", result["summary"],
                       "拦截信息应明确说明 force_execution 参数")
        self.assertIn("True", result["summary"],
                       "拦截信息应明确说明设置为 True")

    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_blocked_response_error_field_is_false(self, mock_risk, mock_sec):
        """拦截是主动行为，error 字段应为 False"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "risk_reasons": ["🔴 Scam"],
        }
        mock_sec.return_value = {
            "checked": True,
            "is_risky": True,
            "risk_type": "Scam",
        }

        from_addr = "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        to_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

        result = build_unsigned_tx(from_addr, to_addr, 10.0, "USDT", force_execution=False)
        self.assertFalse(result.get("error", True),
                         "拦截是主动安全行为，error 应为 False，不是异常")


class TestCallRouterIntegration(unittest.TestCase):
    """
    集成测试: call_router 路由调用时的异常处理
    
    验证 InsufficientBalanceError 在路由层被正确捕获并返回结构化错误。
    """

    @patch('tron_mcp_server.call_router._build_unsigned_tx')
    def test_insufficient_balance_returns_error(self, mock_build):
        """余额不足时，call_router 应返回结构化错误"""
        mock_build.side_effect = InsufficientBalanceError(
            "❌ 交易拒绝: USDT 余额不足",
            "insufficient_usdt",
            {"errors": [{"code": "insufficient_usdt", "message": "USDT 不足"}]},
        )

        result = call_router.call("build_tx", {
            "from": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
            "to": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "amount": 10.0,
            "token": "USDT",
        })

        self.assertTrue(result.get("error"), "余额不足应返回 error=True")
        self.assertEqual(result["error_type"], "insufficient_usdt")

    def test_unknown_action_returns_error(self, ):
        """未知 action 应返回错误而非崩溃"""
        result = call_router.call("nonexistent_action", {})
        self.assertIn("error", result)

    def test_missing_address_returns_error(self):
        """缺少必填参数 address 应返回错误"""
        result = call_router.call("get_usdt_balance", {})
        self.assertIn("error", result)
        self.assertIn("missing_param", str(result.get("error", "")))


# ============================================================================
# 第三部分：交易构建模块 (tx_builder.py) 的单元测试
# ============================================================================

class TestFeeEstimation(unittest.TestCase):
    """
    问题6: 手续费估算误差 / 带宽计算"一刀切"
    
    1. USDT 交易默认消耗 65000 Energy * 420 SUN = 27.3 TRX
    2. 未接入"免费 600 带宽"的动态抵扣
    3. 对于余额刚够 13 TRX 的用户可能误判
    """

    def test_estimated_fee_constants_documented(self):
        """验证手续费相关常量已被正确定义"""
        from tron_mcp_server.tx_builder import (
            FREE_BANDWIDTH_DAILY, USDT_BANDWIDTH_BYTES, BANDWIDTH_PRICE_SUN
        )
        self.assertEqual(ESTIMATED_USDT_ENERGY, 65000, "默认 USDT Energy 应为 65000")
        self.assertEqual(ENERGY_PRICE_SUN, 420, "默认 Energy 价格应为 420 SUN/Energy")
        self.assertEqual(FREE_BANDWIDTH_DAILY, 600, "默认免费带宽应为 600")
        self.assertEqual(USDT_BANDWIDTH_BYTES, 350, "USDT 带宽消耗应为 350 字节")
        self.assertEqual(BANDWIDTH_PRICE_SUN, 1000, "带宽单价应为 1000 SUN")
        
        # 计算修复后的预估手续费:
        # 能量费 = 65000 * 420 = 27,300,000 SUN (27.3 TRX)
        # 带宽费 = max(0, (350 - min(350,600)) * 1000) = 0 SUN (免费带宽覆盖)
        # 总计 = 27,300,000 + 0 = 27,300,000 SUN (27.3 TRX)
        energy_fee = ESTIMATED_USDT_ENERGY * ENERGY_PRICE_SUN  # 27,300,000 SUN
        free_bw_coverage = min(USDT_BANDWIDTH_BYTES, FREE_BANDWIDTH_DAILY)  # 350
        actual_bw_fee = max(0, (USDT_BANDWIDTH_BYTES - free_bw_coverage) * BANDWIDTH_PRICE_SUN)  # 0 SUN
        estimated_fee_sun = energy_fee + actual_bw_fee  # 27,300,000 SUN
        expected_fee_trx = estimated_fee_sun / SUN_PER_TRX  # 27.3 TRX
        self.assertAlmostEqual(expected_fee_trx, 27.3, places=2,
                               msg=f"USDT 手续费 = 能量费 27.3 TRX + 带宽费 0 TRX (免费覆盖)，实际 {expected_fee_trx}")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_borderline_trx_balance_for_usdt_transfer(self, mock_usdt, mock_trx):
        """
        边界测试: 用户有 27.3 TRX（阈值），应允许交易
        免费带宽仅抵扣带宽费（=0），能量费 27.3 TRX 不变
        """
        mock_usdt.return_value = 100.0
        mock_trx.return_value = 27.3  # 刚好等于能量费阈值

        result = check_sender_balance("TAddr1234567890123456789012345678", 10.0, "USDT")
        self.assertTrue(result["sufficient"], "27.3 TRX 刚好够 Gas 阈值，应通过")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_slightly_below_gas_threshold(self, mock_usdt, mock_trx):
        """边界测试: 用户有 27.29 TRX（低于阈值 27.3），应拒绝"""
        mock_usdt.return_value = 100.0
        mock_trx.return_value = 27.29  # 差一点

        with self.assertRaises(InsufficientBalanceError):
            check_sender_balance("TAddr1234567890123456789012345678", 10.0, "USDT")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    @patch('tron_mcp_server.tron_client.get_usdt_balance')
    def test_free_bandwidth_not_deducted(self, mock_usdt, mock_trx):
        """
        修复验证: 免费带宽只抵扣带宽费，不减能量费
        
        在 TRON 网络中，每个地址有 600 免费带宽/天。
        USDT 转账带宽消耗约 350 bytes < 600 → 带宽费 = 0。
        但能量费 65000 * 420 = 27.3 TRX 不变。
        
        总阈值: 27.3 TRX (能量) + 0 TRX (带宽，被免费额度覆盖)
        用户有 27.31 TRX → 应该被允许通过
        """
        mock_usdt.return_value = 100.0
        mock_trx.return_value = 27.31

        # 27.31 TRX > 27.3 TRX 阈值，应该通过
        result = check_sender_balance("TAddr1234567890123456789012345678", 10.0, "USDT")
        self.assertTrue(result["sufficient"], "27.31 TRX 在免费带宽覆盖带宽费后应该够用")

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_transfer_fee_calculation(self, mock_trx):
        """TRX 转账手续费应为 0.1 TRX（100,000 SUN）"""
        mock_trx.return_value = 10.2  # 转 10 TRX + 0.1 TRX Gas = 10.1 TRX

        result = check_sender_balance("TAddr1234567890123456789012345678", 10.0, "TRX")
        self.assertTrue(result["sufficient"])

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_transfer_exact_boundary(self, mock_trx):
        """TRX 转账边界: 恰好 10.1 TRX 应该够转 10 TRX"""
        mock_trx.return_value = 10.1

        result = check_sender_balance("TAddr1234567890123456789012345678", 10.0, "TRX")
        self.assertTrue(result["sufficient"])

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_trx_transfer_insufficient(self, mock_trx):
        """TRX 转账: 只有 10.09 TRX 不够转 10 TRX + 0.1 Gas"""
        mock_trx.return_value = 10.09

        with self.assertRaises(InsufficientBalanceError):
            check_sender_balance("TAddr1234567890123456789012345678", 10.0, "TRX")


class TestRecipientSecurityFallback(unittest.TestCase):
    """
    问题7: check_recipient_security 的降级逻辑
    
    当安全检查 API 失败时，应返回一个明确的"无法检测"标记，
    而不是默认返回安全。
    """

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_security_check_failure_returns_unchecked(self, mock_risk):
        """安全检查 API 失败时，checked 应为 False，并包含降级警告"""
        mock_risk.side_effect = Exception("API failure")

        result = check_recipient_security("TFakeAddr1234567890123456789012345")
        self.assertFalse(result["checked"], "API 失败时 checked 应为 False")
        # 修复后: is_risky 应为 None，而非 False
        self.assertIsNone(result["is_risky"], "API 失败时 is_risky 应为 None，表示无法判断")
        # 修复后: 应包含降级警告
        self.assertIn("degradation_warning", result,
                       "API 失败时应包含 degradation_warning 字段")
        self.assertIn("安全检查服务不可用", result["degradation_warning"],
                       "降级警告应明确提示用户谨慎操作")


# ============================================================================
# 第四部分：架构与工程化问题测试
# ============================================================================

class TestTransactionConfirmation(unittest.TestCase):
    """
    问题8: 缺乏交易状态回执 (Transaction Confirmation)
    
    验证 get_transaction_status 功能是否可用。
    目前 MCP 能查交易状态（已实现），但需验证其在 call_router 中的完整性。
    """

    @patch('tron_mcp_server.tron_client.get_transaction_status')
    def test_transaction_status_success(self, mock_status):
        """查询已确认交易状态"""
        mock_status.return_value = (True, 12345678)

        result = call_router.call("get_transaction_status", {
            "txid": "a" * 64
        })
        self.assertTrue(result.get("success") or result.get("status") == "成功",
                        "确认成功的交易应返回 success=True")

    @patch('tron_mcp_server.tron_client.get_transaction_status')
    def test_transaction_status_pending(self, mock_status):
        """查询 pending 交易不应崩溃"""
        mock_status.side_effect = ValueError("交易不存在或尚未确认")

        result = call_router.call("get_transaction_status", {
            "txid": "b" * 64
        })
        # 应返回 pending 状态而非崩溃
        self.assertIn("status", result)

    def test_transaction_status_invalid_txid(self):
        """无效 txid 应返回错误"""
        result = call_router.call("get_transaction_status", {
            "txid": "invalid"
        })
        self.assertIn("error", result)


class TestExceptionHandlingAudit(unittest.TestCase):
    """
    问题9: 异常捕获过于宽泛 (Silent Failure Audit)
    
    审计项目中所有 except Exception 导致的"静默失效"风险。
    在金融安全工具中，任何静默返回"安全"的异常捕获都是潜在隐患。
    """

    @patch('tron_mcp_server.tron_client.get_balance_trx')
    def test_balance_query_failure_doesnt_block_tx(self, mock_trx):
        """余额查询失败时，不应阻止交易（保守策略），但应标记 checked=False"""
        mock_trx.side_effect = Exception("Network Error")

        result = check_sender_balance("TFakeAddr1234567890123456789012345", 10.0, "USDT")
        self.assertFalse(result["checked"], "查询失败时 checked 应为 False")
        self.assertIsNone(result["sufficient"], "查询失败时 sufficient 应为 None")

    @patch('tron_mcp_server.tron_client.get_account_status')
    def test_recipient_status_failure_doesnt_block_tx(self, mock_status):
        """接收方状态查询失败时，不应阻止交易"""
        mock_status.side_effect = Exception("Timeout")

        result = check_recipient_status("TFakeAddr1234567890123456789012345")
        self.assertFalse(result["checked"], "查询失败时 checked 应为 False")
        self.assertEqual(len(result["warnings"]), 0, "查询失败时不应有 spurious 警告")


class TestFormatterSafety(unittest.TestCase):
    """
    问题10: format_account_safety 的降级行为
    
    当 risk_info 结构不完整时，格式化函数应安全降级。
    """

    def test_format_with_empty_risk_info(self):
        """空 risk_info 不应崩溃"""
        result = formatters.format_account_safety("TAddr1234567890123456789012345678", {})
        self.assertIn("address", result)
        self.assertIn("summary", result)

    def test_format_with_unknown_risk_type(self):
        """risk_type='Unknown' 时应提示谨慎"""
        result = formatters.format_account_safety("TAddr1234567890123456789012345678", {
            "is_risky": False,
            "risk_type": "Unknown",
        })
        self.assertIn("谨慎", result["summary"], "Unknown 风险类型应提示谨慎操作")

    def test_format_with_blue_tag_safe(self):
        """蓝标（官方认证）地址应显示认证信息"""
        result = formatters.format_account_safety("TAddr1234567890123456789012345678", {
            "is_risky": False,
            "risk_type": "Safe",
            "tags": {"Blue": "Binance", "Red": "", "Grey": "", "Public": ""},
        })
        self.assertIn("Binance", result["summary"])

    def test_format_with_risky_address(self):
        """危险地址应在 summary 中明确标识"""
        result = formatters.format_account_safety("TAddr1234567890123456789012345678", {
            "is_risky": True,
            "risk_type": "Scam",
            "risk_reasons": ["🔴 高危标签 (RedTag): Scam"],
            "tags": {"Red": "Scam", "Grey": "", "Blue": "", "Public": ""},
        })
        self.assertTrue(result["is_risky"])
        self.assertIn("⛔", result["summary"])
    
    def test_format_with_partially_verified(self):
        """risk_type='Partially Verified' 时应显示部分验证提示"""
        result = formatters.format_account_safety("TAddr1234567890123456789012345678", {
            "is_risky": False,
            "risk_type": "Partially Verified",
            "risk_reasons": [],
            "tags": {},
        })
        self.assertEqual(result["safety_status"], "部分验证")
        self.assertIn("部分验证", result["summary"])
        self.assertIn("仅部分安全检查通过", result["summary"])
        self.assertFalse(result["is_safe"], "Partially Verified 不应被标记为 is_safe=True")


class TestCheckRecipientSecurityNoneHandling(unittest.TestCase):
    """
    新增测试: check_recipient_security 返回 is_risky=None 时的处理
    
    当安全检查整体抛异常（而非内部 API 失败并优雅降级）时，
    应返回 is_risky=None，而不是 is_risky=False。
    """

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_exception_returns_is_risky_none(self, mock_risk):
        """当 check_account_risk 整体抛异常时，应返回 is_risky=None"""
        mock_risk.side_effect = Exception("Network timeout")
        
        result = check_recipient_security("TFakeAddr1234567890123456789012345")
        
        # 关键修复点：is_risky 应为 None，而非 False
        self.assertIsNone(result["is_risky"], 
                         "异常时 is_risky 应为 None，表示无法判断，而非 False")
        self.assertFalse(result["checked"])
        self.assertEqual(result["risk_type"], "Unknown")
        self.assertIn("degradation_warning", result)
    
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    def test_build_unsigned_tx_with_is_risky_none(self, mock_security, mock_block):
        """build_unsigned_tx 应正确处理 is_risky=None（不触发熔断，但附带警告）"""
        # 模拟区块信息
        mock_block.return_value = {
            "number": 12345678,
            "hash": "0123456789abcdef" * 4
        }
        
        # 模拟安全检查返回 is_risky=None
        mock_security.return_value = {
            "checked": False,
            "is_risky": None,
            "risk_type": "Unknown",
            "security_warning": None,
            "degradation_warning": "⚠️ 安全检查服务不可用，无法验证接收方地址安全性，请谨慎操作",
        }
        
        # 应该成功构建交易（不触发熔断）
        result = build_unsigned_tx(
            from_address="TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
            to_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            amount=10.0,
            token="USDT",
            check_balance=False,  # 跳过余额检查以简化测试
            check_recipient=False,  # 跳过接收方状态检查
            check_security=True,
        )
        
        # 验证交易成功构建
        self.assertNotIn("blocked", result, "is_risky=None 不应触发熔断")
        self.assertIn("raw_data", result, "应成功构建交易")
        
        # 验证降级警告被附加到结果中
        self.assertIn("degradation_warning", result)
        self.assertIn("安全检查服务不可用", result["degradation_warning"])
    
    @patch('tron_mcp_server.tron_client.get_latest_block_info')
    @patch('tron_mcp_server.tx_builder.check_recipient_security')
    def test_build_unsigned_tx_is_risky_none_no_circuit_break(self, mock_security, mock_block):
        """is_risky=None 不应触发熔断机制"""
        # 模拟区块信息
        mock_block.return_value = {
            "number": 12345678,
            "hash": "0123456789abcdef" * 4
        }
        
        mock_security.return_value = {
            "checked": False,
            "is_risky": None,  # 无法判断
            "risk_type": "Unknown",
            "security_warning": None,
            "degradation_warning": "⚠️ 安全检查服务不可用",
        }
        
        result = build_unsigned_tx(
            from_address="TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9",
            to_address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            amount=10.0,
            token="USDT",
            check_balance=False,
            check_recipient=False,
            check_security=True,
            force_execution=False,  # 即使不强制执行，也不应熔断
        )
        
        # is_risky=None 时不应触发熔断（与 is_risky=True 不同）
        self.assertNotIn("blocked", result)
        self.assertFalse(result.get("blocked", False))


class TestCheckAccountSafetyEndToEnd(unittest.TestCase):
    """
    端到端测试: tron_check_account_safety 工具完整调用链
    
    验证从 call_router → tron_client → formatters 的完整路径。
    """

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_check_safety_e2e_safe(self, mock_risk):
        """端到端：安全地址检查"""
        mock_risk.return_value = {
            "is_risky": False,
            "risk_type": "Safe",
            "detail": "Passed all checks",
            "risk_reasons": [],
            "tags": {"Red": "", "Grey": "", "Blue": "", "Public": ""},
        }

        result = call_router.call("check_account_safety", {
            "address": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        })
        self.assertTrue(result.get("is_safe"))
        self.assertFalse(result.get("is_risky"))

    @patch('tron_mcp_server.tron_client.check_account_risk')
    def test_check_safety_e2e_risky(self, mock_risk):
        """端到端：风险地址检查"""
        mock_risk.return_value = {
            "is_risky": True,
            "risk_type": "Scam",
            "detail": "Known scammer",
            "risk_reasons": ["🔴 高危标签 (RedTag): Scam"],
            "tags": {"Red": "Scam", "Grey": "", "Blue": "", "Public": ""},
        }

        result = call_router.call("check_account_safety", {
            "address": "TMuA6YqfCeX8EhbfYEg5y7S4DqzSJireY9"
        })
        self.assertTrue(result.get("is_risky"))
        self.assertFalse(result.get("is_safe"))
        self.assertEqual(result.get("risk_type"), "Scam")


if __name__ == '__main__':
    unittest.main(verbosity=2)
