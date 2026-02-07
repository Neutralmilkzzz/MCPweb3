"""Skills 清单模块 - 渐进式披露核心"""

# 技能清单常量 - 供 call_router 使用
SKILLS = [
    {
        "action": "get_usdt_balance",
        "desc": "查询 USDT (TRC20) 余额",
        "params": {"address": "TRON 地址 (Base58 或 Hex)"},
    },
    {
        "action": "get_gas_parameters",
        "desc": "获取当前网络 Gas 参数 (SUN)",
        "params": {},
    },
    {
        "action": "get_transaction_status",
        "desc": "检查交易确认状态",
        "params": {"txid": "64 位交易哈希"},
    },
    {
        "action": "get_balance",
        "desc": "查询 TRX (原生代币) 余额",
        "params": {"address": "TRON 地址"},
    },
    {
        "action": "get_network_status",
        "desc": "查看网络最新区块高度",
        "params": {},
    },
    {
        "action": "get_account_status",
        "desc": "检查账户激活状态（用于预判转账风险）",
        "params": {"address": "TRON 地址"},
    },
    {
        "action": "check_account_safety",
        "desc": "检查地址是否为恶意地址（钓鱼、诈骗等）",
        "params": {"address": "TRON 地址"},
    },
    {
        "action": "build_tx",
        "desc": "构建未签名转账交易（自动检测接收方账户状态并预警）",
        "params": {
            "from": "发送方地址",
            "to": "接收方地址",
            "amount": "转账数量 (数字)",
            "token": "TRX 或 USDT",
        },
    },
    {
        "action": "broadcast_tx",
        "desc": "广播已签名交易到 TRON 网络",
        "params": {
            "signed_tx_json": "已签名交易的 JSON 字符串",
        },
    },
    {
        "action": "transfer",
        "desc": "一键转账闭环：安全检查 → 构建 → 签名 → 广播",
        "params": {
            "to": "接收方地址",
            "amount": "转账数量 (数字)",
            "token": "TRX 或 USDT",
            "force_execution": "布尔值，强制执行（接收方有风险时）",
        },
    },
    {
        "action": "get_wallet_info",
        "desc": "查看本地钱包地址和余额（不暴露私钥）",
        "params": {},
    },
    {
        "action": "get_transaction_history",
        "desc": "查询地址的交易历史记录（支持自定义条数和代币筛选）",
        "params": {
            "address": "TRON 地址",
            "limit": "返回条数（默认 10，最大 50）",
            "start": "偏移量（默认 0）",
            "token": "代币筛选：TRX / USDT / TRC20合约地址 / TRC10名称（可选）",
        },
    },
    {
        "action": "addressbook_add",
        "desc": "添加或更新地址簿联系人（别名↔地址映射）",
        "params": {
            "alias": "联系人别名（如 小明）",
            "address": "TRON 地址",
            "note": "备注（可选）",
        },
    },
    {
        "action": "addressbook_remove",
        "desc": "删除地址簿中的联系人",
        "params": {"alias": "要删除的联系人别名"},
    },
    {
        "action": "addressbook_lookup",
        "desc": "通过别名查找 TRON 地址（支持模糊搜索）",
        "params": {"alias": "联系人别名"},
    },
    {
        "action": "addressbook_list",
        "desc": "列出地址簿中所有联系人",
        "params": {},
    },
]


def get_skills() -> dict:
    """返回补全的技能清单响应"""
    return {
        "server": "tron-mcp-server",
        "version": "1.0.1",
        "usage": "通过 tron_* 系列工具直接调用",
        "skills": SKILLS,
        "summary": f"已加载 TRON 区块链技能列表，包含 {len(SKILLS)} 个可用动作。",
    }
