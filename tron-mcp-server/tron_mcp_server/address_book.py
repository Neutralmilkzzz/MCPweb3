"""地址簿模块 - 本地地址别名映射存储

使用 JSON 文件持久化存储 TRON 钱包地址的别名映射。
默认存储路径: ~/.tron_mcp/address_book.json
可通过环境变量 TRON_ADDRESSBOOK_PATH 自定义存储路径。
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
from difflib import SequenceMatcher


def _get_storage_path() -> Path:
    """获取地址簿存储路径"""
    custom_path = os.getenv("TRON_ADDRESSBOOK_PATH")
    if custom_path:
        return Path(custom_path)
    
    # 默认路径: ~/.tron_mcp/address_book.json
    home_dir = Path.home()
    tron_dir = home_dir / ".tron_mcp"
    tron_dir.mkdir(parents=True, exist_ok=True)
    return tron_dir / "address_book.json"


def _load_addressbook() -> dict:
    """加载地址簿数据"""
    path = _get_storage_path()
    if not path.exists():
        return {}
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        # 文件损坏或读取失败，返回空字典
        return {}


def _save_addressbook(data: dict) -> None:
    """保存地址簿数据"""
    path = _get_storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_contact(alias: str, address: str, note: str = "") -> dict:
    """
    添加或更新联系人
    
    Args:
        alias: 联系人别名（如 "小明"、"老板"）
        address: TRON 地址（Base58 格式）
        note: 备注信息（可选）
    
    Returns:
        包含 alias, address, note, is_update, total_contacts 的结果字典
    """
    addressbook = _load_addressbook()
    
    # 检查是否为更新操作
    is_update = alias in addressbook
    
    # 保存联系人
    addressbook[alias] = {
        "address": address,
        "note": note,
        "created_at": datetime.now().isoformat() if not is_update else addressbook[alias].get("created_at", datetime.now().isoformat()),
        "updated_at": datetime.now().isoformat() if is_update else None,
    }
    
    _save_addressbook(addressbook)
    
    return {
        "alias": alias,
        "address": address,
        "note": note,
        "is_update": is_update,
        "total_contacts": len(addressbook),
    }


def remove_contact(alias: str) -> dict:
    """
    删除联系人
    
    Args:
        alias: 要删除的联系人别名
    
    Returns:
        包含 alias, found, removed_address, total_contacts 的结果字典
    """
    addressbook = _load_addressbook()
    
    if alias not in addressbook:
        return {
            "alias": alias,
            "found": False,
            "removed_address": None,
            "total_contacts": len(addressbook),
        }
    
    # 删除联系人
    removed_contact = addressbook.pop(alias)
    _save_addressbook(addressbook)
    
    return {
        "alias": alias,
        "found": True,
        "removed_address": removed_contact["address"],
        "total_contacts": len(addressbook),
    }


def lookup(alias: str) -> dict:
    """
    通过别名查找地址（支持模糊搜索）
    
    Args:
        alias: 联系人别名
    
    Returns:
        包含 alias, found, address, note, similar_matches 的结果字典
    """
    addressbook = _load_addressbook()
    
    # 精确匹配
    if alias in addressbook:
        contact = addressbook[alias]
        return {
            "alias": alias,
            "found": True,
            "address": contact["address"],
            "note": contact.get("note", ""),
            "created_at": contact.get("created_at", ""),
        }
    
    # 模糊搜索：查找相似的别名
    similar_matches = []
    for contact_alias, contact_data in addressbook.items():
        # 使用 SequenceMatcher 计算相似度
        similarity = SequenceMatcher(None, alias.lower(), contact_alias.lower()).ratio()
        if similarity > 0.5:  # 相似度阈值 50%
            similar_matches.append({
                "alias": contact_alias,
                "address": contact_data["address"],
                "note": contact_data.get("note", ""),
                "similarity": similarity,
            })
    
    # 按相似度降序排序
    similar_matches.sort(key=lambda x: x["similarity"], reverse=True)
    
    # 只返回前 3 个最相似的结果
    similar_matches = similar_matches[:3]
    
    return {
        "alias": alias,
        "found": False,
        "address": None,
        "note": None,
        "similar_matches": similar_matches,
    }


def list_contacts() -> dict:
    """
    列出所有联系人
    
    Returns:
        包含 total, contacts 列表的结果字典
    """
    addressbook = _load_addressbook()
    
    contacts = []
    for alias, contact_data in addressbook.items():
        contacts.append({
            "alias": alias,
            "address": contact_data["address"],
            "note": contact_data.get("note", ""),
            "created_at": contact_data.get("created_at", ""),
        })
    
    # 按创建时间排序（最新的在前）
    contacts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return {
        "total": len(contacts),
        "contacts": contacts,
    }


def resolve_address(alias_or_address: str) -> str:
    """
    解析地址：如果输入是合法 TRON 地址则直接返回，否则从地址簿查找
    
    这是一个工具函数，用于在转账等场景中自动解析别名。
    
    Args:
        alias_or_address: 别名或 TRON 地址
    
    Returns:
        TRON 地址字符串
    
    Raises:
        ValueError: 如果既不是合法地址也找不到对应的别名
    """
    # 导入 validators 模块（延迟导入避免循环依赖）
    from . import validators
    
    # 如果输入已经是合法地址，直接返回
    if validators.is_valid_address(alias_or_address):
        return alias_or_address
    
    # 否则尝试从地址簿查找
    result = lookup(alias_or_address)
    if result["found"]:
        return result["address"]
    
    # 如果有相似匹配，提示用户
    if result.get("similar_matches"):
        similar = result["similar_matches"][0]
        raise ValueError(
            f"地址簿中未找到「{alias_or_address}」，"
            f"您是否想找「{similar['alias']}」（{similar['address']}）？"
        )
    
    # 完全找不到
    raise ValueError(
        f"无效的地址或别名：{alias_or_address}。"
        f"请使用合法的 TRON 地址，或先通过 tron_addressbook_add 添加别名。"
    )
