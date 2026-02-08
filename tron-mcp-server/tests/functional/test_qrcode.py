"""
测试 QR Code 生成功能
=====================

覆盖以下功能：
- qrcode_generator.generate_address_qrcode: 生成钱包地址二维码
- call_router._handle_generate_qrcode: 路由处理函数
- formatters.format_qrcode_result: 格式化结果
"""

import unittest
import sys
import os
import tempfile
import shutil
from pathlib import Path

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import MagicMock

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()

from tron_mcp_server import qrcode_generator
from tron_mcp_server import formatters
from tron_mcp_server import call_router


class TestQRCodeGenerator(unittest.TestCase):
    """测试 qrcode_generator 模块"""

    def setUp(self):
        """创建临时目录"""
        self.test_dir = tempfile.mkdtemp()
        self.test_address = "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn"

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_generate_qrcode_default_dir(self):
        """测试在默认目录生成二维码"""
        result = qrcode_generator.generate_address_qrcode(
            address=self.test_address,
        )

        # 验证返回结果
        self.assertIn("file_path", result)
        self.assertIn("address", result)
        self.assertIn("file_size", result)
        self.assertEqual(result["address"], self.test_address)

        # 验证文件存在
        self.assertTrue(os.path.exists(result["file_path"]))

        # 验证文件大小
        self.assertGreater(result["file_size"], 0)

        # 清理生成的文件
        if os.path.exists(result["file_path"]):
            os.remove(result["file_path"])
        # 尝试删除qrcodes目录
        qrcodes_dir = os.path.dirname(result["file_path"])
        if os.path.exists(qrcodes_dir) and not os.listdir(qrcodes_dir):
            os.rmdir(qrcodes_dir)

    def test_generate_qrcode_custom_dir(self):
        """测试在自定义目录生成二维码"""
        result = qrcode_generator.generate_address_qrcode(
            address=self.test_address,
            output_dir=self.test_dir,
        )

        # 验证文件在正确的目录
        self.assertTrue(result["file_path"].startswith(self.test_dir))
        self.assertTrue(os.path.exists(result["file_path"]))

    def test_generate_qrcode_custom_filename(self):
        """测试自定义文件名"""
        custom_name = "my_wallet_qr"
        result = qrcode_generator.generate_address_qrcode(
            address=self.test_address,
            output_dir=self.test_dir,
            filename=custom_name,
        )

        # 验证文件名
        self.assertTrue(result["file_path"].endswith(f"{custom_name}.png"))
        self.assertTrue(os.path.exists(result["file_path"]))

    def test_qrcode_file_size(self):
        """测试生成的二维码文件大小合理"""
        result = qrcode_generator.generate_address_qrcode(
            address=self.test_address,
            output_dir=self.test_dir,
        )

        # 二维码文件应该在合理的大小范围内 (100 bytes to 10KB)
        self.assertGreater(result["file_size"], 100)
        self.assertLess(result["file_size"], 10 * 1024)


class TestQRCodeFormatter(unittest.TestCase):
    """测试 formatters.format_qrcode_result 函数"""

    def test_format_qrcode_result_basic(self):
        """测试基本格式化"""
        input_data = {
            "file_path": "/tmp/qrcodes/qr_TKyPzHiX_CcCchn.png",
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
            "file_size": 1234,
        }

        result = formatters.format_qrcode_result(input_data)

        # 验证返回字段
        self.assertIn("file_path", result)
        self.assertIn("address", result)
        self.assertIn("file_size", result)
        self.assertIn("summary", result)

        # 验证 summary 包含关键信息（地址被截断显示）
        self.assertIn("TKyPzHiXW4...zZpiCchn", result["summary"])
        self.assertIn("/tmp/qrcodes/qr_TKyPzHiX_CcCchn.png", result["summary"])
        self.assertIn("1.2 KB", result["summary"])

    def test_format_qrcode_result_small_file(self):
        """测试小文件大小显示（Bytes）"""
        input_data = {
            "file_path": "/tmp/test.png",
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
            "file_size": 500,
        }

        result = formatters.format_qrcode_result(input_data)

        # 验证小文件显示为 Bytes
        self.assertIn("500 Bytes", result["summary"])

    def test_format_qrcode_result_large_file(self):
        """测试大文件大小显示（KB）"""
        input_data = {
            "file_path": "/tmp/test.png",
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
            "file_size": 5120,
        }

        result = formatters.format_qrcode_result(input_data)

        # 验证大文件显示为 KB
        self.assertIn("5.0 KB", result["summary"])


class TestCallRouterQRCode(unittest.TestCase):
    """测试 call_router 的 QR Code 相关处理"""

    def setUp(self):
        """创建临时目录"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """清理临时目录"""
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_handle_generate_qrcode_success(self):
        """测试成功生成二维码"""
        result = call_router.call("generate_qrcode", {
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
            "output_dir": self.test_dir,
        })

        # 验证返回结果
        self.assertIn("file_path", result)
        self.assertIn("address", result)
        self.assertIn("summary", result)
        self.assertNotIn("error", result)

        # 验证文件存在
        self.assertTrue(os.path.exists(result["file_path"]))

    def test_handle_generate_qrcode_missing_address(self):
        """测试缺少 address 参数"""
        result = call_router.call("generate_qrcode", {})

        # 验证返回错误
        self.assertIn("error", result)
        self.assertIn("missing_param", result["error"])

    def test_handle_generate_qrcode_invalid_address(self):
        """测试无效地址"""
        result = call_router.call("generate_qrcode", {
            "address": "invalid_address_123",
        })

        # 验证返回错误
        self.assertIn("error", result)
        self.assertIn("invalid_address", result["error"])

    def test_handle_generate_qrcode_with_custom_filename(self):
        """测试自定义文件名"""
        result = call_router.call("generate_qrcode", {
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
            "output_dir": self.test_dir,
            "filename": "my_custom_qr",
        })

        # 验证文件名
        self.assertIn("my_custom_qr.png", result["file_path"])
        self.assertTrue(os.path.exists(result["file_path"]))


if __name__ == "__main__":
    unittest.main()
