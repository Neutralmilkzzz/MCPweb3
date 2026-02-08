"""
测试 config.py 和 logging_config.py - 配置和日志模块
====================================================

覆盖以下功能的集成测试：
- config.get_api_url: 获取 TRONSCAN API URL
- config.get_api_key: 获取 API Key
- config.get_timeout: 获取超时设置
- logging_config.setup_logging: 日志初始化
- skills.get_skills: 技能清单
"""

import unittest
import sys
import os
import logging

os.chdir("../tron-mcp-server")

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import config
from tron_mcp_server import logging_config
from tron_mcp_server import skills


class TestGetApiUrl(unittest.TestCase):
    """测试 config.get_api_url"""

    def test_default_url(self):
        """默认 URL"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TRONSCAN_API_URL", None)
            result = config.get_api_url()
            self.assertIn("tronscan", result.lower())

    def test_custom_url(self):
        """自定义 URL"""
        with patch.dict(os.environ, {"TRONSCAN_API_URL": "https://custom.api.io"}):
            result = config.get_api_url()
            self.assertEqual(result, "https://custom.api.io")


class TestGetApiKey(unittest.TestCase):
    """测试 config.get_api_key"""

    def test_no_key_returns_empty(self):
        """未配置 API Key 返回空字符串"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("TRONSCAN_API_KEY", None)
            result = config.get_api_key()
            self.assertEqual(result, "")

    def test_configured_key(self):
        """配置了 API Key 应返回"""
        with patch.dict(os.environ, {"TRONSCAN_API_KEY": "test-key-123"}):
            result = config.get_api_key()
            self.assertEqual(result, "test-key-123")


class TestGetTimeout(unittest.TestCase):
    """测试 config.get_timeout"""

    def test_default_timeout(self):
        """默认超时应为正数"""
        result = config.get_timeout()
        self.assertIsInstance(result, (int, float))
        self.assertGreater(result, 0)

    def test_custom_timeout(self):
        """自定义超时"""
        with patch.dict(os.environ, {"REQUEST_TIMEOUT": "30.0"}):
            result = config.get_timeout()
            self.assertEqual(result, 30.0)


class TestSetupLogging(unittest.TestCase):
    """测试 logging_config.setup_logging"""

    def test_setup_logging_runs_without_error(self):
        """setup_logging 应不抛出异常"""
        logging_config.setup_logging()

    def test_logger_is_configured(self):
        """配置后 logger 应正常工作"""
        logging_config.setup_logging()
        logger = logging.getLogger("tron_mcp_server")
        # 日志不应抛出异常
        logger.info("Test log message")
        logger.debug("Debug message")


class TestGetSkills(unittest.TestCase):
    """测试 skills.get_skills"""

    def test_returns_dict(self):
        """应返回字典"""
        result = skills.get_skills()
        self.assertIsInstance(result, dict)

    def test_has_skills_list(self):
        """应包含 skills 列表"""
        result = skills.get_skills()
        self.assertIn("skills", result)
        self.assertIsInstance(result["skills"], list)

    def test_skills_not_empty(self):
        """技能列表不应为空"""
        result = skills.get_skills()
        self.assertGreater(len(result["skills"]), 0)

    def test_skill_structure(self):
        """每个技能应包含 action、desc、params"""
        result = skills.get_skills()
        for skill in result["skills"]:
            self.assertIn("action", skill)
            self.assertIn("desc", skill)
            self.assertIn("params", skill)

    def test_has_summary(self):
        """应包含 summary"""
        result = skills.get_skills()
        self.assertIn("summary", result)

    def test_has_server_info(self):
        """应包含 server 和 version"""
        result = skills.get_skills()
        self.assertIn("server", result)
        self.assertIn("version", result)

    def test_all_expected_actions_present(self):
        """应包含所有预期的动作"""
        result = skills.get_skills()
        actions = [s["action"] for s in result["skills"]]
        expected = [
            "get_usdt_balance", "get_gas_parameters", "get_transaction_status",
            "get_balance", "get_network_status", "get_account_status",
            "check_account_safety", "build_tx", "broadcast_tx", "transfer",
            "get_wallet_info", "get_transaction_history",
        ]
        for action in expected:
            self.assertIn(action, actions, f"缺少动作: {action}")


class TestSkillsConstants(unittest.TestCase):
    """测试 skills.SKILLS 常量"""

    def test_skills_is_list(self):
        """SKILLS 应为列表"""
        self.assertIsInstance(skills.SKILLS, list)

    def test_skills_count(self):
        """SKILLS 数量应大于 10"""
        self.assertGreaterEqual(len(skills.SKILLS), 10)


if __name__ == "__main__":
    unittest.main()
