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
]


def get_skills() -> dict:
    """返回补全的技能清单响应"""
    return {
        "server": "tron-mcp-server",
        "version": "1.0.1",
        "usage": "通过 call(action='xxx', params={...}) 调用",
        "skills": SKILLS,
        "summary": f"已加载 TRON 区块链技能列表，包含 {len(SKILLS)} 个可用动作。",
    }
