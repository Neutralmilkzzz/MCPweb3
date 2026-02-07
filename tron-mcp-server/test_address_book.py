"""
测试 address_book.py 地址簿模块
=================================

覆盖场景：
1. 添加联系人（新增和更新）
2. 删除联系人（存在和不存在）
3. 精确查找
4. 模糊搜索
5. 列出所有联系人
6. resolve_address 函数（合法地址直接返回 vs 别名查找）
7. 空地址簿场景
8. 地址验证（通过 call_router 调用时验证地址格式）
"""

import unittest
import sys
import os
import tempfile
import json
from pathlib import Path

# 强制 UTF-8 编码
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# 将项目目录加入 path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from unittest.mock import patch, MagicMock

# 创建 MockFastMCP
class MockFastMCP:
    """Mock FastMCP that returns the original function from decorator"""
    def __init__(self, name):
        self.name = name
    
    def tool(self):
        def decorator(func):
            return func
        return decorator

# 模拟 mcp 依赖
sys.modules["mcp"] = MagicMock()
sys.modules["mcp.server"] = MagicMock()
sys.modules["mcp.server.fastmcp"] = MagicMock()
sys.modules["mcp.server.fastmcp"].FastMCP = MockFastMCP

from tron_mcp_server import address_book


class TestAddressBook(unittest.TestCase):
    """测试地址簿核心功能"""

    def setUp(self):
        """为每个测试创建临时文件路径"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_address_book.json"
        # Mock 环境变量指向临时文件
        self.env_patcher = patch.dict(os.environ, {"TRON_ADDRESSBOOK_PATH": str(self.temp_file)})
        self.env_patcher.start()

    def tearDown(self):
        """清理临时文件"""
        self.env_patcher.stop()
        if self.temp_file.exists():
            self.temp_file.unlink()
        if Path(self.temp_dir).exists():
            Path(self.temp_dir).rmdir()

    def test_add_contact_new(self):
        """测试添加新联系人"""
        result = address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", "大学同学")
        
        self.assertEqual(result["alias"], "小明")
        self.assertEqual(result["address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["note"], "大学同学")
        self.assertFalse(result["is_update"])
        self.assertEqual(result["total_contacts"], 1)

    def test_add_contact_update(self):
        """测试更新现有联系人"""
        # 先添加
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", "大学同学")
        
        # 再更新
        result = address_book.add_contact("小明", "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn", "新地址")
        
        self.assertEqual(result["alias"], "小明")
        self.assertEqual(result["address"], "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn")
        self.assertEqual(result["note"], "新地址")
        self.assertTrue(result["is_update"])
        self.assertEqual(result["total_contacts"], 1)

    def test_remove_contact_exists(self):
        """测试删除存在的联系人"""
        # 先添加
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        # 删除
        result = address_book.remove_contact("小明")
        
        self.assertEqual(result["alias"], "小明")
        self.assertTrue(result["found"])
        self.assertEqual(result["removed_address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["total_contacts"], 0)

    def test_remove_contact_not_exists(self):
        """测试删除不存在的联系人"""
        result = address_book.remove_contact("不存在的人")
        
        self.assertEqual(result["alias"], "不存在的人")
        self.assertFalse(result["found"])
        self.assertIsNone(result["removed_address"])
        self.assertEqual(result["total_contacts"], 0)

    def test_lookup_exact_match(self):
        """测试精确匹配查找"""
        # 添加联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", "大学同学")
        
        # 精确查找
        result = address_book.lookup("小明")
        
        self.assertEqual(result["alias"], "小明")
        self.assertTrue(result["found"])
        self.assertEqual(result["address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(result["note"], "大学同学")

    def test_lookup_fuzzy_search(self):
        """测试模糊搜索"""
        # 添加多个联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        address_book.add_contact("小红", "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn")
        address_book.add_contact("老王", "TPepEjJgigAbcGWkxnyjdCE2X8ZQanAXbW")
        
        # 模糊搜索 "小" 应该找到小明和小红
        result = address_book.lookup("小")
        
        self.assertFalse(result["found"])
        self.assertIsNotNone(result.get("similar_matches"))
        self.assertGreater(len(result["similar_matches"]), 0)
        
        # 检查相似匹配中是否包含小明和小红
        aliases = [m["alias"] for m in result["similar_matches"]]
        self.assertIn("小明", aliases)
        self.assertIn("小红", aliases)

    def test_lookup_not_found(self):
        """测试查找不存在的联系人（无相似结果）"""
        result = address_book.lookup("根本不存在")
        
        self.assertFalse(result["found"])
        self.assertIsNone(result["address"])
        self.assertEqual(len(result.get("similar_matches", [])), 0)

    def test_list_contacts_empty(self):
        """测试列出空地址簿"""
        result = address_book.list_contacts()
        
        self.assertEqual(result["total"], 0)
        self.assertEqual(len(result["contacts"]), 0)

    def test_list_contacts_multiple(self):
        """测试列出多个联系人"""
        # 添加多个联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", "同学")
        address_book.add_contact("老板", "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn", "公司")
        address_book.add_contact("家人", "TPepEjJigAbcGWkxnyjdCE2X8ZQanAXbW")
        
        result = address_book.list_contacts()
        
        self.assertEqual(result["total"], 3)
        self.assertEqual(len(result["contacts"]), 3)
        
        # 检查是否包含所有联系人
        aliases = [c["alias"] for c in result["contacts"]]
        self.assertIn("小明", aliases)
        self.assertIn("老板", aliases)
        self.assertIn("家人", aliases)

    def test_resolve_address_valid_address(self):
        """测试 resolve_address：输入是合法地址，直接返回"""
        valid_address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        result = address_book.resolve_address(valid_address)
        
        self.assertEqual(result, valid_address)

    def test_resolve_address_alias_found(self):
        """测试 resolve_address：输入是别名，从地址簿查找"""
        # 添加联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        # 通过别名解析
        result = address_book.resolve_address("小明")
        
        self.assertEqual(result, "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")

    def test_resolve_address_alias_not_found(self):
        """测试 resolve_address：输入既不是地址也不是别名"""
        with self.assertRaises(ValueError) as context:
            address_book.resolve_address("不存在的别名")
        
        self.assertIn("无效的地址或别名", str(context.exception))

    def test_resolve_address_similar_match(self):
        """测试 resolve_address：别名未找到但有相似匹配"""
        # 添加联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        
        with self.assertRaises(ValueError) as context:
            address_book.resolve_address("小")
        
        # 应该提示相似匹配
        self.assertIn("您是否想找", str(context.exception))
        self.assertIn("小明", str(context.exception))

    def test_storage_persistence(self):
        """测试数据持久化"""
        # 添加联系人
        address_book.add_contact("小明", "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", "同学")
        
        # 直接读取文件验证
        with open(self.temp_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        self.assertIn("小明", data)
        self.assertEqual(data["小明"]["address"], "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7")
        self.assertEqual(data["小明"]["note"], "同学")


class TestAddressBookViaCallRouter(unittest.TestCase):
    """测试通过 call_router 调用地址簿功能（验证地址校验）"""

    def setUp(self):
        """为每个测试创建临时文件路径"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_address_book.json"
        self.env_patcher = patch.dict(os.environ, {"TRON_ADDRESSBOOK_PATH": str(self.temp_file)})
        self.env_patcher.start()

    def tearDown(self):
        """清理临时文件"""
        self.env_patcher.stop()
        if self.temp_file.exists():
            self.temp_file.unlink()
        if Path(self.temp_dir).exists():
            Path(self.temp_dir).rmdir()

    def test_add_contact_invalid_address_via_router(self):
        """测试通过 call_router 添加联系人时验证地址格式"""
        from tron_mcp_server import call_router
        
        # 尝试添加无效地址
        result = call_router.call("addressbook_add", {
            "alias": "测试",
            "address": "invalid_address",
            "note": "测试备注",
        })
        
        # 应该返回错误
        self.assertIn("error", result)
        self.assertIn("无效的地址格式", result.get("summary", ""))

    def test_add_contact_valid_address_via_router(self):
        """测试通过 call_router 添加联系人（合法地址）"""
        from tron_mcp_server import call_router
        
        result = call_router.call("addressbook_add", {
            "alias": "小明",
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "note": "大学同学",
        })
        
        # 应该成功
        self.assertIn("summary", result)
        self.assertIn("已添加联系人", result["summary"])

    def test_lookup_via_router(self):
        """测试通过 call_router 查找联系人"""
        from tron_mcp_server import call_router
        
        # 先添加
        call_router.call("addressbook_add", {
            "alias": "小明",
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
        })
        
        # 查找
        result = call_router.call("addressbook_lookup", {"alias": "小明"})
        
        self.assertIn("summary", result)
        self.assertIn("小明", result["summary"])
        self.assertIn("TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7", result["summary"])

    def test_list_via_router(self):
        """测试通过 call_router 列出所有联系人"""
        from tron_mcp_server import call_router
        
        # 添加多个联系人
        call_router.call("addressbook_add", {
            "alias": "小明",
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
        })
        call_router.call("addressbook_add", {
            "alias": "老板",
            "address": "TKyPzHiXW4Zms4txUxfWjXBidGzZpiCchn",
        })
        
        # 列出
        result = call_router.call("addressbook_list", {})
        
        self.assertIn("summary", result)
        self.assertIn("地址簿共 2 位联系人", result["summary"])

    def test_remove_via_router(self):
        """测试通过 call_router 删除联系人"""
        from tron_mcp_server import call_router
        
        # 先添加
        call_router.call("addressbook_add", {
            "alias": "小明",
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
        })
        
        # 删除
        result = call_router.call("addressbook_remove", {"alias": "小明"})
        
        self.assertIn("summary", result)
        self.assertIn("已删除联系人", result["summary"])


if __name__ == "__main__":
    unittest.main()
