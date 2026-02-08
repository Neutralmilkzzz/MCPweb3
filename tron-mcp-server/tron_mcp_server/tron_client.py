"""TRON 客户端模块 - TRONSCAN REST API 封装"""

import logging
import os
from typing import Optional
import httpx
import base58

from . import config

logger = logging.getLogger(__name__)

# USDT TRC20 合约地址 — 根据 TRON_NETWORK 自动切换
USDT_CONTRACT_BASE58 = config.get_usdt_contract()
USDT_CONTRACT_HEX = config.get_usdt_contract_hex()

# 超时设置
TIMEOUT = config.get_timeout()


def _get_api_url() -> str:
    """获取 TRONSCAN API URL"""
    base_url = config.get_api_url()
    base_url = base_url.rstrip("/")
    if not base_url:
        raise ValueError("未配置 TRONSCAN_API_URL")
    return base_url


def _get_headers() -> dict:
    """获取请求头"""
    headers = {"Accept": "application/json"}
    api_key = config.get_api_key()
    if api_key:
        # TRONSCAN API 要求使用 TRON-PRO-API-KEY 作为 header 名称
        headers["TRON-PRO-API-KEY"] = api_key
    return headers


def _get(path: str, params: Optional[dict] = None) -> dict:
    """发送 GET 请求"""
    url = f"{_get_api_url()}/{path.lstrip('/')}"
    response = httpx.get(url, params=params, headers=_get_headers(), timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if data is None:
        raise ValueError("TRONSCAN 响应为空")
    return data


def _to_int(value) -> int:
    if value is None:
        raise ValueError("缺少数值字段")
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("0x"):
            return int(value, 16)
        return int(value)
    raise ValueError(f"无法解析数值: {value}")


def _first_not_none(*values):
    for value in values:
        if value is not None:
            return value
    return None


def _get_account(address: str) -> dict:
    return _get("account", {"address": _normalize_address(address)})


def _normalize_address(address: str) -> str:
    if address.startswith("0x") and len(address) == 44:
        return _hex_to_base58(address[2:])
    if address.startswith("41") and len(address) == 42:
        return _hex_to_base58(address)
    return address


def _normalize_txid(txid: str) -> str:
    return txid[2:] if txid.startswith("0x") else txid


def _hex_to_base58(hex_addr: str) -> str:
    """将十六进制地址转换为 Base58Check 格式"""
    raw = bytes.fromhex(hex_addr)
    return base58.b58encode_check(raw).decode('utf-8')


def get_usdt_balance(address: str) -> float:
    """
    查询地址的 USDT 余额
    调用 TRONSCAN account 接口
    """
    data = _get_account(address)
    token_balances = _first_not_none(
        data.get("trc20token_balances"),
        data.get("trc20TokenBalances"),
        data.get("tokenBalances"),
        [],
    )

    for entry in token_balances:
        token_id = (
            entry.get("tokenId")
            or entry.get("token_id")
            or entry.get("contractAddress")
            or entry.get("contract_address")
            or entry.get("tokenAddress")
        )
        if token_id in (USDT_CONTRACT_BASE58, USDT_CONTRACT_HEX):
            balance_raw = _to_int(
                _first_not_none(
                    entry.get("balance"),
                    entry.get("tokenBalance"),
                    entry.get("quantity"),
                    entry.get("token_balance"),
                )
            )
            decimals = _first_not_none(
                entry.get("tokenDecimal"),
                entry.get("token_decimals"),
                entry.get("decimals"),
            )
            decimals = int(decimals) if decimals is not None else 6
            return balance_raw / (10 ** decimals)

    return 0.0


def get_balance_trx(address: str) -> float:
    """
    查询地址的 TRX 余额
    TRONSCAN 返回 SUN
    """
    data = _get_account(address)
    balance_sun = _to_int(
        _first_not_none(
            data.get("balance"),
            data.get("balanceSun"),
            data.get("totalBalance"),
            data.get("total_balance"),
            0,  # 兜底值：新地址余额为 0
        )
    )
    return balance_sun / 1_000_000


def get_gas_parameters() -> int:
    """
    获取当前网络 Gas 价格 (SUN)
    """
    data = _get("chainparameters")
    params = (
        data.get("tronParameters")
        or data.get("chainParameter")
        or data.get("chainParameters")
        or data
    )
    if not isinstance(params, list):
        raise ValueError("TRONSCAN 响应缺少 chainParameter")

    def _find_param(key: str):
        for item in params:
            if item.get("key") == key or item.get("name") == key:
                return item.get("value") or item.get("valueStr")
        return None

    value = _find_param("getEnergyFee")
    if value is None:
        value = _find_param("getTransactionFee")
    if value is None:
        raise ValueError("TRONSCAN 响应缺少能量费用参数")
    return _to_int(value)


def get_transaction_status(txid: str) -> dict:
    """
    查询交易状态，返回详细信息字典：
    - success: 是否成功
    - block_number: 所在区块
    - token_type: 货币类型 (TRX / USDT / 其他 TRC20)
    - amount: 转账金额（已换算为可读单位）
    - from_address: 发送方地址
    - to_address: 接收方地址
    - timestamp: 交易时间戳 (毫秒)
    - fee: 手续费 (SUN)
    """
    data = _get("transaction-info", {"hash": _normalize_txid(txid)})
    if not data:
        raise ValueError("交易不存在或尚未确认")

    contract_ret = data.get("contractRet") or data.get("contract_result")
    success = contract_ret == "SUCCESS"

    block_number = _to_int(
        data.get("block")
        or data.get("blockNumber")
        or data.get("block_number")
        or 0
    )

    # 提取转账金额、货币类型、发送方、接收方
    token_type = "TRX"
    amount = 0.0
    from_address = data.get("ownerAddress") or data.get("owner_address") or ""
    to_address = data.get("toAddress") or data.get("to_address") or ""

    # 检查是否为 TRC20 转账 (trigger_info / tokenTransferInfo)
    trigger_info = data.get("trigger_info") or data.get("triggerInfo") or {}
    token_transfer = data.get("tokenTransferInfo") or data.get("token_transfer_info") or {}
    contract_type = data.get("contractType") or data.get("contract_type") or 0

    if token_transfer:
        # TRC20 转账
        symbol = token_transfer.get("symbol") or token_transfer.get("tokenName") or "TRC20"
        decimals = _to_int(token_transfer.get("decimals") or 6)
        raw_amount = _to_int(token_transfer.get("amount_str") or token_transfer.get("amount") or 0)
        amount = raw_amount / (10 ** decimals)
        token_type = symbol
        to_address = token_transfer.get("to_address") or token_transfer.get("toAddress") or to_address
        from_address = token_transfer.get("from_address") or token_transfer.get("fromAddress") or from_address
    elif trigger_info and trigger_info.get("method"):
        # 其他合约调用
        method = trigger_info.get("method", "")
        if "transfer" in method.lower():
            # 尝试从 trigger_info 提取
            param_value = trigger_info.get("parameter", {}).get("_value") or trigger_info.get("call_value") or 0
            token_type = trigger_info.get("tokenName") or "TRC20"
            decimals = _to_int(trigger_info.get("decimals") or 6)
            amount = _to_int(param_value) / (10 ** decimals)
        else:
            token_type = "合约调用"
    else:
        # TRX 原生转账
        raw_amount = _to_int(
            data.get("amount") or data.get("contractData", {}).get("amount") or 0
        )
        amount = raw_amount / 1_000_000
        token_type = "TRX"

    # 时间戳和手续费
    timestamp = _to_int(data.get("timestamp") or data.get("block_timestamp") or 0)
    fee = _to_int(data.get("cost", {}).get("fee") or data.get("fee") or 0)

    return {
        "success": success,
        "block_number": block_number,
        "token_type": token_type,
        "amount": amount,
        "from_address": from_address,
        "to_address": to_address,
        "timestamp": timestamp,
        "fee": fee,
    }


def get_network_status() -> int:
    """
    获取当前网络区块高度
    """
    data = _get("block", {"sort": "-number", "limit": 1, "start": 0})
    blocks = data.get("data") if isinstance(data, dict) else None
    if not blocks:
        raise KeyError("TRONSCAN 响应缺少区块数据")
    return _to_int(blocks[0].get("number") or blocks[0].get("blockNumber"))


def get_latest_block_info() -> dict:
    """
    获取最新区块信息（用于构建交易）
    """
    data = _get("block", {"sort": "-number", "limit": 1, "start": 0})
    blocks = data.get("data") if isinstance(data, dict) else None
    if not blocks:
        raise ValueError("TRONSCAN 未返回最新区块")
    block = blocks[0]
    return {
        "number": _to_int(block.get("number") or block.get("blockNumber")),
        "hash": block.get("hash") or block.get("blockHash") or block.get("blockID"),
    }


def check_account_risk(address: str) -> dict:
    """
    基于 TRONSCAN 官方接口 (AccountV2 + Security) 的深度体检。
    返回包含所有标签、黑名单、投诉状态的完整报告。
    
    Deep Risk Scanning using official TRONSCAN APIs:
    1. Account Detail API (/api/accountv2): redTag, greyTag, blueTag, feedbackRisk
    2. Security Service API (/api/security/account/data): is_black_list, fraud_token_creator, etc.
    
    Risk Detection Logic (as per TRONSCAN guidelines):
    - redTag is not empty → High Risk (Scam/Phishing)
    - greyTag is not empty → Suspicious/Disputed
    - feedbackRisk is true → User-reported Risk
    - is_black_list is true → Blacklisted by stablecoin issuers
    - has_fraud_transaction is true → Fraud history
    - fraud_token_creator is true → Fake token creator
    - send_ad_by_memo is true → Spam account
    
    Args:
        address: TRON 地址 (Base58Check 格式)
    
    Returns:
        包含风险信息的字典:
        - is_risky: 地址是否存在任何风险标记
        - risk_reasons: 所有风险原因列表（用于展示）
        - tags: 所有标签字典 (Red, Grey, Blue, Public)
        - details: API 原始数据
        - risk_type: 主要风险类型 (兼容旧接口)
        - detail: 详细说明 (兼容旧接口)
        - raw_info: 原始风险数据字符串 (兼容旧接口)
    """
    normalized_addr = _normalize_address(address)
    headers = _get_headers()
    
    # 初始化完整报告结构
    report = {
        "is_risky": False,
        "risk_reasons": [],  # 存具体的风险描述
        "tags": {},          # 存所有原始标签，供展示
        "details": {}        # 存 API 原始数据
    }
    
    # Initialize risk indicators
    red_tag = ""
    grey_tag = ""
    blue_tag = ""
    public_tag = ""
    feedback_risk = False
    is_black_list = False
    has_fraud_transaction = False
    fraud_token_creator = False
    send_ad_by_memo = False
    
    data_v2 = {}
    data_sec = {}
    v2_success = False
    sec_success = False
    
    # --- Layer 1: Account V2 API (查标签 + 投诉) ---
    try:
        account_url = "https://apilist.tronscanapi.com/api/accountv2"
        response = httpx.get(account_url, params={"address": normalized_addr}, headers=headers, timeout=TIMEOUT)
        data_v2 = response.json()
        v2_success = True
        
        red_tag = data_v2.get("redTag") or ""
        grey_tag = data_v2.get("greyTag") or ""
        blue_tag = data_v2.get("blueTag") or ""
        public_tag = data_v2.get("publicTag") or ""
        feedback_risk = bool(data_v2.get("feedbackRisk", False))
        
    except Exception as e:
        logger.warning(f"Account detail API failed for {normalized_addr}: {e}")
    
    # 保存所有标签（无论是否有风险，蓝标对用户也有参考价值）
    report["tags"] = {
        "Red": red_tag,
        "Grey": grey_tag,
        "Blue": blue_tag,
        "Public": public_tag
    }
    
    # 🚨 风险判定逻辑 A: 标签类
    if red_tag:
        report["is_risky"] = True
        report["risk_reasons"].append(f"🔴 高危标签 (RedTag): {red_tag}")
    
    if grey_tag:
        report["is_risky"] = True
        report["risk_reasons"].append(f"⚪ 灰度存疑 (GreyTag): {grey_tag}")
    
    if feedback_risk:
        report["is_risky"] = True
        report["risk_reasons"].append("⚠️ 用户投诉 (FeedbackRisk): 存在多起举报")
    
    # 特殊处理 Public Tag: 如果包含 suspicious 等词
    if public_tag and any(x in str(public_tag).lower() for x in ["suspicious", "hack", "scam"]):
        report["is_risky"] = True
        report["risk_reasons"].append(f"⚠️ 公共标签警示: {public_tag}")
    
    # --- Layer 2: Security Service API (查黑产行为) ---
    try:
        security_url = "https://apilist.tronscanapi.com/api/security/account/data"
        response = httpx.get(security_url, params={"address": normalized_addr}, headers=headers, timeout=TIMEOUT)
        data_sec = response.json()
        sec_success = True
        
        is_black_list = bool(data_sec.get("is_black_list", False))
        has_fraud_transaction = bool(data_sec.get("has_fraud_transaction", False))
        fraud_token_creator = bool(data_sec.get("fraud_token_creator", False))
        send_ad_by_memo = bool(data_sec.get("send_ad_by_memo", False))
        
    except Exception as e:
        logger.warning(f"Security service API failed for {normalized_addr}: {e}")
    
    # 🚨 风险判定逻辑 B: 行为类
    if is_black_list:
        report["is_risky"] = True
        report["risk_reasons"].append("💀 USDT/稳定币黑名单 (Blacklist)")
    
    if has_fraud_transaction:
        report["is_risky"] = True
        report["risk_reasons"].append("💸 曾有欺诈交易记录 (Fraud History)")
    
    if fraud_token_creator:
        report["is_risky"] = True
        report["risk_reasons"].append("🪙 假币创建者 (Fake Token Creator)")
    
    if send_ad_by_memo:
        report["is_risky"] = True
        report["risk_reasons"].append("📢 垃圾广告账号 (Spam Sender)")
    
    # 保存 API 原始数据
    report["details"] = {"v2": data_v2, "sec": data_sec}
    
    # Build raw_info for AI Agent transparency (兼容旧接口)
    raw_info = (
        f"redTag:[{red_tag}] greyTag:[{grey_tag}] blueTag:[{blue_tag}] "
        f"publicTag:[{public_tag}] feedbackRisk:[{feedback_risk}] "
        f"is_black_list:[{is_black_list}] has_fraud_transaction:[{has_fraud_transaction}] "
        f"fraud_token_creator:[{fraud_token_creator}] send_ad_by_memo:[{send_ad_by_memo}]"
    )
    report["raw_info"] = raw_info
    
    # --- 兼容旧接口：设置 risk_type 和 detail ---
    if red_tag:
        report["risk_type"] = red_tag
        report["detail"] = f"TRONSCAN flagged this address as {red_tag}."
    elif is_black_list:
        report["risk_type"] = "Blacklisted"
        report["detail"] = "Address is on stablecoin (e.g. USDT) blacklist."
    elif feedback_risk:
        report["risk_type"] = "User Reported"
        report["detail"] = "Address has been reported by multiple users as risky."
    elif fraud_token_creator:
        report["risk_type"] = "Fraud Token Creator"
        report["detail"] = "Address has created fraudulent/fake tokens."
    elif has_fraud_transaction:
        report["risk_type"] = "Fraud Transaction"
        report["detail"] = "Address has fraud transaction history."
    elif grey_tag:
        report["risk_type"] = f"Grey: {grey_tag}"
        report["detail"] = f"Address has a grey tag: {grey_tag}."
    elif send_ad_by_memo:
        report["risk_type"] = "Spam Account"
        report["detail"] = "Address frequently sends advertisements via memo (spam behavior)."
    else:
        # 关键修复：区分 "真安全" 和 "无法验证"
        # 如果两个 API 都失败了，不能声称地址安全
        if not v2_success and not sec_success:
            report["risk_type"] = "Unknown"
            report["detail"] = "Unable to verify: all security APIs failed. Please proceed with caution."
            report["risk_reasons"].append("⚠️ 安全检查服务不可用，无法验证地址安全性，请谨慎操作")
        elif not v2_success or not sec_success:
            # 只有一个 API 失败，部分检查通过
            report["risk_type"] = "Partially Verified"
            report["detail"] = "Partial verification: one security API was unavailable. No risk found in available data."
        else:
            report["risk_type"] = "Safe"
            report["detail"] = "Passed all security checks."
    
    return report


def broadcast_transaction(signed_tx: dict) -> dict:
    """
    广播已签名的交易到 TRON 网络
    
    Args:
        signed_tx: 已签名的交易字典，需包含 txID, raw_data, signature 字段
    
    Returns:
        广播结果字典，包含 result (bool) 和 txid
    
    Raises:
        ValueError: 交易格式无效或广播失败
    """
    if "signature" not in signed_tx or not signed_tx["signature"]:
        raise ValueError("交易未签名：缺少 signature 字段")

    url = "https://api.trongrid.io/wallet/broadcasttransaction"
    headers = _get_headers()
    headers["Content-Type"] = "application/json"

    response = httpx.post(url, json=signed_tx, headers=headers, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if not data.get("result", False):
        error_msg = data.get("message", "Unknown error")
        # TronGrid returns hex-encoded error messages
        if isinstance(error_msg, str):
            try:
                error_msg = bytes.fromhex(error_msg).decode("utf-8", errors="replace")
            except (ValueError, UnicodeDecodeError):
                pass
        raise ValueError(f"广播失败: {error_msg}")

    return {
        "result": True,
        "txid": data.get("txid", signed_tx.get("txID", "")),
    }


def get_account_status(address: str) -> dict:
    """
    检查账户激活状态
    
    返回账户状态信息:
    - is_activated: 账户是否已激活（有过交易历史）
    - has_trx: 账户是否持有 TRX
    - trx_balance: TRX 余额 (SUN)
    - total_transactions: 交易总数
    
    用途：
    1. 向未激活地址转账 TRC20 会消耗更多 Energy（SSTORE 指令）
    2. 如果接收方没有 TRX，可能无法转出代币
    """
    data = _get_account(_normalize_address(address))
    
    # 获取 TRX 余额 (SUN)
    trx_balance = _to_int(
        _first_not_none(
            data.get("balance"),
            data.get("balanceSun"),
            data.get("totalBalance"),
            data.get("total_balance"),
            0,
        )
    )
    
    # 获取交易次数
    total_transactions = _to_int(
        _first_not_none(
            data.get("transactions"),
            data.get("totalTransactionCount"),
            data.get("total_transaction_count"),
            data.get("transactionCount"),
            0,
        )
    )
    
    # 账户是否已激活（有过交易历史或有余额）
    is_activated = total_transactions > 0 or trx_balance > 0
    
    # 是否持有 TRX
    has_trx = trx_balance > 0
    
    return {
        "address": _normalize_address(address),
        "is_activated": is_activated,
        "has_trx": has_trx,
        "trx_balance_sun": trx_balance,
        "trx_balance": trx_balance / 1_000_000,
        "total_transactions": total_transactions,
    }


def get_transfer_history(address: str, limit: int = 10, start: int = 0, token: Optional[str] = None) -> dict:
    """
    查询 TRX 和 TRC10 转账记录
    调用 TRONSCAN 端点：/api/transfer
    
    Args:
        address: TRON 地址
        limit: 返回条数，默认 10
        start: 偏移量，默认 0
        token: 可选，按代币名称筛选（如 "_" 表示 TRX，或 TRC10 token name）
    
    Returns:
        API 响应字典（包含 total 和 data 列表）
    """
    normalized_addr = _normalize_address(address)
    params = {
        "sort": "-timestamp",
        "limit": limit,
        "start": start,
        "address": normalized_addr,
    }
    if token is not None:
        params["token"] = token
    
    return _get("transfer", params)


def get_trc20_transfer_history(
    address: str,
    limit: int = 10,
    start: int = 0,
    contract_address: Optional[str] = None
) -> dict:
    """
    查询 TRC20 代币（如 USDT）转账记录
    调用 TRONSCAN 端点：/api/token_trc20/transfers
    
    Args:
        address: TRON 地址
        limit: 返回条数，默认 10
        start: 偏移量，默认 0
        contract_address: 可选，过滤特定合约地址（如 USDT 合约）
    
    Returns:
        API 响应字典（包含 total 和 token_transfers 列表）
    """
    normalized_addr = _normalize_address(address)
    params = {
        "sort": "-timestamp",
        "limit": limit,
        "start": start,
        "relatedAddress": normalized_addr,
    }
    if contract_address is not None:
        params["contract_address"] = contract_address
    
    return _get("token_trc20/transfers", params)


def get_internal_transactions(address: str, limit: int = 20, start: int = 0) -> dict:
    """
    查询地址的内部交易（合约内部调用产生的转账）
    调用 TRONSCAN 端点：/api/internal-transaction
    
    Args:
        address: TRON 地址
        limit: 返回条数，默认 20
        start: 偏移量，默认 0
    
    Returns:
        API 响应字典（包含 total 和 data 列表）
    """
    normalized_addr = _normalize_address(address)
    params = {
        "sort": "-timestamp",
        "limit": limit,
        "start": start,
        "address": normalized_addr,
    }
    return _get("internal-transaction", params)


def get_account_tokens(address: str) -> dict:
    """
    查询地址持有的所有代币列表（TRC20 + TRC10 + TRX）
    复用 /api/account 接口，提取全量代币持仓信息
    
    Args:
        address: TRON 地址
    
    Returns:
        包含 address, token_count, tokens 列表的字典
    """
    data = _get_account(address)
    
    tokens = []
    
    # TRX 余额
    trx_balance_sun = _to_int(
        _first_not_none(
            data.get("balance"),
            data.get("balanceSun"),
            data.get("totalBalance"),
            0,
        )
    )
    tokens.append({
        "token_name": "TRX",
        "token_abbr": "TRX",
        "token_type": "native",
        "contract_address": "",
        "balance_raw": trx_balance_sun,
        "decimals": 6,
        "balance": trx_balance_sun / 1_000_000,
    })
    
    # TRC20 代币
    trc20_balances = _first_not_none(
        data.get("trc20token_balances"),
        data.get("trc20TokenBalances"),
        [],
    )
    for entry in trc20_balances:
        contract_addr = (
            entry.get("tokenId")
            or entry.get("contractAddress")
            or entry.get("contract_address")
            or ""
        )
        token_name = entry.get("tokenName") or ""
        token_abbr = entry.get("tokenAbbr") or token_name
        balance_raw = _to_int(
            _first_not_none(entry.get("balance"), entry.get("tokenBalance"), 0)
        )
        decimals = int(entry.get("tokenDecimal") or entry.get("decimals") or 6)
        
        tokens.append({
            "token_name": token_name,
            "token_abbr": token_abbr,
            "token_type": "trc20",
            "contract_address": contract_addr,
            "balance_raw": balance_raw,
            "decimals": decimals,
            "balance": balance_raw / (10 ** decimals),
        })
    
    # TRC10 代币 (tokenBalances 中 non-TRX)
    token_balances = data.get("tokenBalances") or []
    for entry in token_balances:
        name = entry.get("tokenName") or entry.get("name") or ""
        if name in ("_", "TRX", ""):
            continue  # 已在 TRX 余额中处理
        decimals_val = int(entry.get("tokenDecimal") or 0)
        balance_raw = _to_int(entry.get("balance") or 0)
        tokens.append({
            "token_name": name,
            "token_abbr": entry.get("tokenAbbr") or name,
            "token_type": "trc10",
            "contract_address": "",
            "balance_raw": balance_raw,
            "decimals": decimals_val,
            "balance": balance_raw / (10 ** decimals_val) if decimals_val > 0 else balance_raw,
        })
    
    return {
        "address": _normalize_address(address),
        "token_count": len(tokens),
        "tokens": tokens,
    }


def get_account_energy(address: str) -> dict:
    """
    查询账户能量(Energy)资源情况
    
    调用 TRONSCAN /api/accountv2 接口获取资源信息。
    
    Args:
        address: TRON 地址
    
    Returns:
        包含 energy_limit, energy_used, energy_remaining 等字段的字典
    """
    normalized = _normalize_address(address)
    data = _get("accountv2", {"address": normalized})
    
    # 从响应中提取 Energy 相关字段
    energy_limit = _to_int(_first_not_none(
        data.get("energyLimit"),
        data.get("energy_limit"),
        0,
    ))
    energy_used = _to_int(_first_not_none(
        data.get("energyUsed"),
        data.get("energy_used"),
        0,
    ))
    energy_remaining = _to_int(_first_not_none(
        data.get("remainingEnergy"),
        data.get("remaining_energy"),
        max(0, energy_limit - energy_used),
    ))
    frozen_for_energy = _to_int(_first_not_none(
        data.get("frozenForEnergy"),
        data.get("frozen_for_energy"),
        0,
    ))
    delegated_for_energy = _to_int(_first_not_none(
        data.get("delegateFrozenForEnergy"),
        data.get("delegate_frozen_for_energy"),
        0,
    ))
    
    return {
        "address": normalized,
        "energy_limit": energy_limit,
        "energy_used": energy_used,
        "energy_remaining": energy_remaining,
        "frozen_for_energy_sun": frozen_for_energy,
        "frozen_for_energy_trx": frozen_for_energy / 1_000_000,
        "delegated_for_energy_sun": delegated_for_energy,
        "delegated_for_energy_trx": delegated_for_energy / 1_000_000,
    }


def get_account_bandwidth(address: str) -> dict:
    """
    查询账户带宽(Bandwidth)资源情况
    
    调用 TRONSCAN /api/accountv2 接口获取资源信息。
    
    Args:
        address: TRON 地址
    
    Returns:
        包含 free_net_limit, free_net_used, net_limit, net_used 等字段的字典
    """
    normalized = _normalize_address(address)
    data = _get("accountv2", {"address": normalized})
    
    # 免费带宽（每天约 600 点）
    free_net_limit = _to_int(_first_not_none(
        data.get("freeNetLimit"),
        data.get("free_net_limit"),
        600,  # TRON 默认每账户每天 600 免费带宽
    ))
    free_net_used = _to_int(_first_not_none(
        data.get("freeNetUsed"),
        data.get("free_net_used"),
        0,
    ))
    free_net_remaining = max(0, free_net_limit - free_net_used)
    
    # 质押获得的带宽
    net_limit = _to_int(_first_not_none(
        data.get("netLimit"),
        data.get("net_limit"),
        0,
    ))
    net_used = _to_int(_first_not_none(
        data.get("netUsed"),
        data.get("net_used"),
        0,
    ))
    net_remaining = max(0, net_limit - net_used)
    
    # 质押的 TRX 数量
    frozen_for_bandwidth = _to_int(_first_not_none(
        data.get("freezeAmountForBandwidth"),
        data.get("freeze_amount_for_bandwidth"),
        data.get("frozenForBandwidth"),
        0,
    ))
    delegated_for_bandwidth = _to_int(_first_not_none(
        data.get("acquiredDelegateFrozenForBandWidth"),
        data.get("acquired_delegate_frozen_for_bandwidth"),
        0,
    ))
    
    # 汇总
    total_limit = free_net_limit + net_limit
    total_used = free_net_used + net_used
    total_remaining = free_net_remaining + net_remaining
    
    return {
        "address": normalized,
        "free_net_limit": free_net_limit,
        "free_net_used": free_net_used,
        "free_net_remaining": free_net_remaining,
        "net_limit": net_limit,
        "net_used": net_used,
        "net_remaining": net_remaining,
        "total_bandwidth": total_limit,
        "total_used": total_used,
        "total_remaining": total_remaining,
        "frozen_for_bandwidth_sun": frozen_for_bandwidth,
        "frozen_for_bandwidth_trx": frozen_for_bandwidth / 1_000_000,
        "delegated_for_bandwidth_sun": delegated_for_bandwidth,
        "delegated_for_bandwidth_trx": delegated_for_bandwidth / 1_000_000,
    }
