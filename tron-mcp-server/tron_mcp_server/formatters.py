"""格式化模块 - 结构化输出 + 自然语言摘要"""

import json

from .tron_client import _normalize_address

# 资源消耗常量 (Resource Cost Constants)
USDT_TRANSFER_ENERGY_COST = 65000  # 每笔 USDT 转账约消耗的 Energy
TRX_TRANSFER_BANDWIDTH_COST = 270  # 每笔 TRX 转账约消耗的带宽（字节）
USDT_TRANSFER_BANDWIDTH_COST = 350  # 每笔 USDT 转账约消耗的带宽（字节）


def _safe_normalize_address(address: str) -> str:
    """安全归一化 TRON 地址（hex 转 Base58），失败时返回原值。"""
    if not address:
        return ""
    try:
        return _normalize_address(address)
    except (ValueError, TypeError):
        return address


def format_usdt_balance(address: str, balance_raw: int) -> dict:
    """
    格式化 USDT 余额
    USDT TRC20 使用 6 位小数
    """
    balance_usdt = balance_raw / 1_000_000
    return {
        "address": address,
        "balance_raw": balance_raw,
        "balance_usdt": balance_usdt,
        "summary": f"地址 {address} 当前 USDT 余额为 {balance_usdt:,.6f} USDT。",
    }


def format_trx_balance(address: str, balance_sun: int) -> dict:
    """
    格式化 TRX 余额
    1 TRX = 1,000,000 SUN
    """
    balance_trx = balance_sun / 1_000_000
    return {
        "address": address,
        "balance_sun": balance_sun,
        "balance_trx": balance_trx,
        "summary": f"地址 {address} 当前 TRX 余额为 {balance_trx:,.6f} TRX。",
    }


def format_gas_parameters(gas_price_sun: int, energy_price_sun: int = None) -> dict:
    """格式化 Gas 参数"""
    gas_price_trx = gas_price_sun / 1_000_000
    result = {
        "gas_price_sun": gas_price_sun,
        "gas_price_trx": gas_price_trx,
        "summary": f"当前网络 Gas 价格为 {gas_price_sun} SUN（约 {gas_price_trx:.6f} TRX）。",
    }
    if energy_price_sun is not None:
        result["energy_price_sun"] = energy_price_sun
    return result


def format_tx_status(
    txid: str, tx_info: dict, confirmations: int = 0
) -> dict:
    """格式化交易状态（含货币类型、金额、发送方、接收方等详细信息）"""
    success = tx_info.get("success", False)
    block_number = tx_info.get("block_number", 0)
    token_type = tx_info.get("token_type", "未知")
    amount = tx_info.get("amount", 0)
    from_address = tx_info.get("from_address", "")
    to_address = tx_info.get("to_address", "")
    timestamp = tx_info.get("timestamp", 0)
    fee_sun = tx_info.get("fee", 0)
    fee_trx = fee_sun / 1_000_000 if fee_sun else 0

    status = "成功" if success else "失败"

    # 格式化时间
    time_str = ""
    if timestamp:
        import datetime
        dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

    # 构建摘要
    summary_parts = [
        f"交易 {txid[:16]}... 状态：{status}",
        f"类型：{token_type} 转账",
        f"金额：{amount:g} {token_type}",
    ]
    if from_address:
        summary_parts.append(f"发送方：{from_address}")
    if to_address:
        summary_parts.append(f"接收方：{to_address}")
    summary_parts.append(f"所在区块：{block_number:,}")
    if fee_trx:
        summary_parts.append(f"手续费：{fee_trx:g} TRX")
    if time_str:
        summary_parts.append(f"时间：{time_str}")

    return {
        "txid": txid,
        "status": status,
        "success": success,
        "block_number": block_number,
        "confirmations": confirmations,
        "token_type": token_type,
        "amount": amount,
        "from_address": from_address,
        "to_address": to_address,
        "fee_sun": fee_sun,
        "fee_trx": fee_trx,
        "timestamp": timestamp,
        "time": time_str,
        "summary": "\n".join(summary_parts),
    }


def format_network_status(block_number: int) -> dict:
    """格式化网络状态"""
    return {
        "latest_block": block_number,
        "chain": "TRON Mainnet",
        "summary": f"TRON 主网当前区块高度为 {block_number:,}。",
    }


def format_account_status(account_status: dict) -> dict:
    """
    格式化账户状态检查结果
    
    用于向用户展示接收方账户的激活状态和潜在风险
    """
    address = account_status.get("address", "")
    is_activated = account_status.get("is_activated", False)
    has_trx = account_status.get("has_trx", False)
    trx_balance = account_status.get("trx_balance", 0)
    total_transactions = account_status.get("total_transactions", 0)
    
    # 构建状态描述
    status_text = "已激活" if is_activated else "未激活"
    
    # 构建预警信息
    warnings = []
    if not is_activated:
        warnings.append("⚠️ 账户未激活，向此地址转账 TRC20 代币将消耗更多 Energy（约 65000 额外能量）")
    if not has_trx:
        warnings.append("⚠️ 账户没有 TRX 余额，可能无法转出收到的代币（需要 TRX 支付手续费）")
    
    # 构建摘要
    summary_parts = [f"地址 {address} 账户状态：{status_text}，TRX 余额 {trx_balance:,.6f} TRX，交易记录 {total_transactions} 笔。"]
    if warnings:
        summary_parts.extend(warnings)
    
    return {
        "address": address,
        "is_activated": is_activated,
        "has_trx": has_trx,
        "trx_balance": trx_balance,
        "total_transactions": total_transactions,
        "warnings": warnings,
        "summary": " ".join(summary_parts),
    }


def format_account_safety(address: str, risk_info: dict) -> dict:
    """
    格式化账户安全检查结果（全量反馈模式）
    
    无论是红标 Scam、蓝标 Binance、灰标、还是被投诉，全部展示给用户。
    如果是蓝标，用户看了也放心；如果是红标，用户看着死心。
    
    Args:
        address: TRON 地址
        risk_info: 来自 tron_client.check_account_risk() 的结果
    
    Returns:
        包含安全检查结果的字典
    """
    is_risky = risk_info.get("is_risky", False)
    risk_type = risk_info.get("risk_type", "Unknown")
    detail = risk_info.get("detail", "")
    risk_reasons = risk_info.get("risk_reasons", [])
    tags = risk_info.get("tags", {})
    
    # 构建预警信息
    warnings = []
    if is_risky and risk_reasons:
        # 使用详细的风险原因列表
        warnings.extend(risk_reasons)
    elif is_risky:
        warnings.append(f"⛔ 警告：该地址已被 TRONSCAN 标记为 {risk_type}")
        if detail:
            warnings.append(f"详情：{detail}")
    
    # 构建标签展示信息
    tag_info = []
    if tags.get("Red"):
        tag_info.append(f"🔴 红标: {tags['Red']}")
    if tags.get("Grey"):
        tag_info.append(f"⚪ 灰标: {tags['Grey']}")
    if tags.get("Blue"):
        tag_info.append(f"🔵 蓝标: {tags['Blue']} (官方认证)")
    if tags.get("Public"):
        tag_info.append(f"📋 公共标签: {tags['Public']}")
    
    # 构建安全状态
    # 关键：risk_type 为 Unknown 或 Partially Verified 时，不能声称安全
    is_unknown = risk_type == "Unknown"
    is_partially_verified = risk_type == "Partially Verified"
    is_safe = not is_risky and not is_unknown and not is_partially_verified
    
    if is_unknown:
        safety_status = "无法验证"
    elif is_partially_verified:
        safety_status = "部分验证"
    elif is_safe:
        safety_status = "安全"
    else:
        safety_status = f"危险（{risk_type}）"
    
    # 构建摘要
    if is_unknown:
        summary = f"地址 {address} 安全检查完成：⚠️ 无法验证: 安全检查服务不可用，请谨慎操作。"
    elif is_partially_verified:
        summary = f"地址 {address} 安全检查完成：⚠️ 部分验证: 仅部分安全检查通过，已检查数据未发现风险，但请注意部分检查不可用。"
    elif is_safe:
        if tags.get("Blue"):
            summary = f"地址 {address} 安全检查完成：✅ 地址安全，且为官方认证机构 ({tags['Blue']})。"
        else:
            summary = f"地址 {address} 安全检查完成：✅ 未在已知风险数据库中发现该地址。"
    else:
        reasons_text = " | ".join(risk_reasons) if risk_reasons else risk_type
        summary = f"地址 {address} 安全检查完成：⛔ 危险！{reasons_text}"
    
    return {
        "address": address,
        "is_safe": is_safe,
        "is_risky": is_risky,
        "risk_type": risk_type,
        "safety_status": safety_status,
        "risk_reasons": risk_reasons,
        "tags": tags,
        "tag_info": tag_info,
        "warnings": warnings,
        "detail": detail,
        "summary": summary,
    }


def format_error(error_code: str, message: str) -> dict:
    """格式化错误响应"""
    return {
        "error": error_code,
        "summary": f"{message}。请调用 action='skills' 查看可用操作。",
    }


def format_signed_tx(
    signed_tx: dict,
    from_addr: str,
    to_addr: str,
    amount: float,
    token: str,
) -> dict:
    """格式化已签名交易结果"""
    tx_id = signed_tx.get("txID", "")
    return {
        "signed_tx": signed_tx,
        "signed_tx_json": json.dumps(signed_tx),
        "txID": tx_id,
        "summary": (
            f"已签名交易: 从 {from_addr[:8]}... 向 {to_addr[:8]}... "
            f"转账 {amount} {token}，txID: {tx_id[:16]}...。"
            f"请使用 tron_broadcast_tx 广播此交易。"
        ),
    }


def format_broadcast_result(result: dict) -> dict:
    """格式化广播结果"""
    tx_id = result.get("txid", "")
    return {
        "result": True,
        "txid": tx_id,
        "summary": (
            f"✅ 交易已成功广播到 TRON 网络！txID: {tx_id}。"
            f"可使用 tron_get_transaction_status 查询确认状态。"
        ),
    }


def format_transfer_result(
    broadcast_result: dict,
    from_addr: str,
    to_addr: str,
    amount: float,
    token: str,
    security_check: dict = None,
    recipient_check: dict = None,
) -> dict:
    """格式化一键转账结果"""
    tx_id = broadcast_result.get("txid", "")
    result = {
        "result": True,
        "txid": tx_id,
        "from": from_addr,
        "to": to_addr,
        "amount": amount,
        "token": token,
        "summary": (
            f"✅ 转账成功！从 {from_addr[:8]}... 向 {to_addr[:8]}... "
            f"转账 {amount} {token}。\n"
            f"交易 ID: {tx_id}\n"
            f"可使用 tron_get_transaction_status 查询确认状态。"
        ),
    }
    if security_check:
        result["security_check"] = security_check
    if recipient_check:
        result["recipient_check"] = recipient_check
    return result


def format_wallet_info(
    address: str,
    trx_balance: float,
    usdt_balance: float,
) -> dict:
    """格式化钱包信息"""
    return {
        "address": address,
        "trx_balance": trx_balance,
        "usdt_balance": usdt_balance,
        "summary": (
            f"💰 当前钱包地址: {address}\n"
            f"TRX 余额: {trx_balance:,.6f} TRX\n"
            f"USDT 余额: {usdt_balance:,.6f} USDT"
        ),
    }


def format_transaction_history(
    address: str,
    transfers: list,
    total: int,
    token_filter: str = None,
    limit: int = 10,
) -> dict:
    """
    格式化交易历史记录
    
    将交易列表格式化为简洁的 dict，提取关键字段并计算方向
    
    Args:
        address: 查询的 TRON 地址
        transfers: 从 API 获取的交易记录列表
        total: 总交易数
        token_filter: 代币筛选条件
        limit: 请求的返回条数
    
    Returns:
        格式化的交易历史结果
    """
    formatted_transfers = []
    normalized_address = _safe_normalize_address(address)
    
    for tx in transfers:
        # 提取交易哈希
        txid = tx.get("transactionHash") or tx.get("transaction_id") or ""
        
        # 提取发送方和接收方地址
        from_addr = tx.get("transferFromAddress") or tx.get("from_address") or tx.get("from") or ""
        to_addr = tx.get("transferToAddress") or tx.get("to_address") or tx.get("to") or ""
        from_addr = _safe_normalize_address(from_addr)
        to_addr = _safe_normalize_address(to_addr)
        
        # 提取金额（使用显式 None 检查避免零值被跳过）
        amount_raw = tx.get("quant")
        if amount_raw is None:
            amount_raw = tx.get("value")
        if amount_raw is None:
            amount_raw = tx.get("amount")
        if amount_raw is None:
            amount_raw = 0
        
        # 提取代币信息
        token_name = ""
        decimals = 6  # 默认精度
        
        # TRC20 token 信息
        token_info = tx.get("tokenInfo")
        if token_info and isinstance(token_info, dict):
            token_name = token_info.get("tokenAbbr") or token_info.get("tokenName") or ""
            token_decimal = token_info.get("tokenDecimal")
            if token_decimal is not None:
                decimals = int(token_decimal)
        
        # TRX/TRC10 token 信息
        if not token_name:
            token_name = tx.get("tokenName") or tx.get("symbol") or ""
        
        # 特殊处理 TRX（_ 表示 TRX）
        if token_name == "_":
            token_name = "TRX"
            decimals = 6
        
        # 转换金额为人类可读格式
        try:
            amount = int(amount_raw) / (10 ** decimals)
        except (ValueError, TypeError):
            amount = 0.0
        
        # 提取时间戳
        timestamp = tx.get("timestamp") or tx.get("block_ts") or 0
        
        # 计算方向
        direction = "OTHER"
        if from_addr and to_addr:
            if from_addr == normalized_address:
                if to_addr == normalized_address:
                    direction = "SELF"
                else:
                    direction = "OUT"
            elif to_addr == normalized_address:
                direction = "IN"
        
        formatted_transfers.append({
            "txid": txid,
            "from": from_addr,
            "to": to_addr,
            "amount": amount,
            "token": token_name,
            "timestamp": timestamp,
            "direction": direction,
        })
    
    # 构建摘要
    filter_text = ""
    if token_filter:
        filter_text = f"（筛选条件：{token_filter}）"
    
    summary = (
        f"地址 {normalized_address} 共有 {total} 笔交易记录{filter_text}，"
        f"当前显示最近 {len(formatted_transfers)} 笔。"
    )
    
    return {
        "address": normalized_address,
        "total": total,
        "displayed": len(formatted_transfers),
        "token_filter": token_filter,
        "transfers": formatted_transfers,
        "summary": summary,
    }


def format_internal_transactions(
    address: str,
    internal_txs: list,
    total: int,
    limit: int = 20,
) -> dict:
    """
    格式化内部交易记录
    
    内部交易是智能合约执行过程中产生的转账，不同于普通的直接转账。
    
    Args:
        address: 查询的 TRON 地址
        internal_txs: 从 API 获取的内部交易记录列表
        total: 总交易数
        limit: 请求的返回条数
    
    Returns:
        格式化的内部交易结果
    """
    formatted_txs = []
    
    for tx in internal_txs:
        # 提取交易哈希
        txid = tx.get("hash") or tx.get("transactionHash") or tx.get("transaction_id") or ""
        
        # 提取调用方和接收方地址
        caller_addr = tx.get("callerAddress") or tx.get("caller_address") or tx.get("from") or ""
        to_addr = tx.get("transferToAddress") or tx.get("to_address") or tx.get("to") or ""
        
        # 提取金额（callValueInfo 数组）
        call_value_info = tx.get("callValueInfo") or []
        amount = 0
        token = "TRX"
        
        if call_value_info and isinstance(call_value_info, list) and len(call_value_info) > 0:
            value_info = call_value_info[0]
            amount_raw = value_info.get("callValue") or 0
            token_id = (value_info.get("tokenId") or "trx").lower()
            
            if token_id == "trx":
                token = "TRX"
                amount = int(amount_raw) / 1_000_000
            else:
                # TRC10 或其他代币
                token = token_id
                amount = int(amount_raw) / 1_000_000  # 假设 6 位小数
        
        # 提取时间戳
        timestamp = tx.get("timestamp") or 0
        
        # 是否回退（失败）
        revert = tx.get("revert", False)
        
        # 备注
        note = tx.get("note") or ""
        
        formatted_txs.append({
            "txid": txid,
            "caller": caller_addr,
            "to": to_addr,
            "amount": amount,
            "token": token,
            "timestamp": timestamp,
            "revert": revert,
            "note": note,
        })
    
    # 构建摘要
    summary = (
        f"地址 {address} 共有 {total} 笔内部交易记录，"
        f"当前显示最近 {len(formatted_txs)} 笔。"
    )
    
    if len(formatted_txs) > 0:
        # 统计成功和失败的交易
        success_count = sum(1 for tx in formatted_txs if not tx["revert"])
        failed_count = len(formatted_txs) - success_count
        summary += f" 成功 {success_count} 笔"
        if failed_count > 0:
            summary += f"，失败 {failed_count} 笔"
        summary += "。"
    
    return {
        "address": address,
        "total": total,
        "displayed": len(formatted_txs),
        "internal_transactions": formatted_txs,
        "summary": summary,
    }


def format_account_tokens(
    address: str,
    tokens: list,
    token_count: int,
) -> dict:
    """
    格式化账户代币列表
    
    Args:
        address: 查询的 TRON 地址
        tokens: 代币列表（包含 token_name, token_abbr, balance 等字段）
        token_count: 代币总数
    
    Returns:
        格式化的代币持仓结果
    """
    # 构建摘要，列举前几个代币
    summary_parts = [f"地址 {address} 持有 {token_count} 种代币"]
    
    if token_count > 0:
        # 列举前 5 个代币
        token_list = []
        for i, token in enumerate(tokens[:5]):
            token_abbr = token.get("token_abbr", "")
            balance = token.get("balance", 0)
            # 格式化余额，避免科学计数法
            if balance >= 1:
                token_list.append(f"{token_abbr} ({balance:,.2f})")
            else:
                token_list.append(f"{token_abbr} ({balance:.6f})")
        
        if token_count > 5:
            summary_parts.append(f"：{', '.join(token_list)}...")
        else:
            summary_parts.append(f"：{', '.join(token_list)}")
    
    summary = "".join(summary_parts) + "。"
    
    return {
        "address": address,
        "token_count": token_count,
        "tokens": tokens,
        "summary": summary,
    }


# ============ 地址簿格式化 ============

def format_addressbook_add(result: dict) -> dict:
    """格式化地址簿添加结果"""
    alias = result["alias"]
    address = result["address"]
    note = result.get("note", "")
    is_update = result.get("is_update", False)
    total = result.get("total_contacts", 0)

    action = "更新" if is_update else "添加"
    note_text = f"，备注：{note}" if note else ""
    summary = (
        f"📒 已{action}联系人「{alias}」→ {address}{note_text}。"
        f"地址簿当前共 {total} 位联系人。"
    )
    return {**result, "summary": summary}


def format_addressbook_remove(result: dict) -> dict:
    """格式化地址簿删除结果"""
    alias = result["alias"]
    found = result.get("found", False)
    total = result.get("total_contacts", 0)

    if found:
        removed_addr = result.get("removed_address", "")
        summary = (
            f"📒 已删除联系人「{alias}」（原地址 {removed_addr}）。"
            f"地址簿当前共 {total} 位联系人。"
        )
    else:
        summary = f"📒 地址簿中未找到名为「{alias}」的联系人。"
    return {**result, "summary": summary}


def format_addressbook_lookup(result: dict) -> dict:
    """格式化地址簿查找结果"""
    alias = result["alias"]
    found = result.get("found", False)

    if found:
        address = result["address"]
        note = result.get("note", "")
        note_text = f"（备注：{note}）" if note else ""
        summary = f"📒 「{alias}」的地址是 {address}{note_text}。"
    else:
        similar = result.get("similar_matches", [])
        if similar:
            match_text = "、".join(
                f"「{m['alias']}」→ {m['address']}" for m in similar
            )
            summary = (
                f"📒 未找到「{alias}」的精确匹配，但找到相似联系人：{match_text}。"
            )
        else:
            summary = f"📒 地址簿中未找到「{alias}」，请先使用 tron_addressbook_add 添加。"
    return {**result, "summary": summary}


def format_addressbook_list(result: dict) -> dict:
    """格式化地址簿列表"""
    total = result.get("total", 0)
    contacts = result.get("contacts", [])

    if total == 0:
        summary = "📒 地址簿为空。使用 tron_addressbook_add 添加联系人。"
    else:
        lines = [f"📒 地址簿共 {total} 位联系人："]
        for c in contacts:
            note_text = f"（{c['note']}）" if c.get("note") else ""
            lines.append(f"  • {c['alias']} → {c['address']}{note_text}")
        summary = "\n".join(lines)
    return {**result, "summary": summary}


def format_account_energy(result: dict) -> dict:
    """格式化账户能量信息"""
    address = result["address"]
    energy_limit = result["energy_limit"]
    energy_used = result["energy_used"]
    energy_remaining = result["energy_remaining"]
    
    usage_pct = (energy_used / energy_limit * 100) if energy_limit > 0 else 0
    
    lines = [f"⚡ 地址 {address} 能量 (Energy) 资源情况："]
    
    if energy_limit == 0 and energy_used == 0:
        lines.append(f"  当前无能量额度（未质押 TRX 获取能量）")
        lines.append(f"  执行合约操作（如 USDT 转账）将直接燃烧 TRX 支付能量费用")
    else:
        lines.append(f"  总额度: {energy_limit:,}")
        lines.append(f"  已使用: {energy_used:,} ({usage_pct:.1f}%)")
        lines.append(f"  剩余: {energy_remaining:,}")
    
    # USDT 转账参考
    usdt_transfers = energy_remaining // USDT_TRANSFER_ENERGY_COST if energy_remaining > 0 else 0
    if usdt_transfers > 0:
        lines.append(f"  📌 当前能量约可免费执行 {usdt_transfers} 笔 USDT 转账（每笔约 {USDT_TRANSFER_ENERGY_COST:,} Energy）")
    elif energy_limit > 0:
        lines.append(f"  📌 能量已耗尽，USDT 转账将燃烧 TRX 支付费用")
    
    return {**result, "summary": "\n".join(lines)}


def format_account_bandwidth(result: dict) -> dict:
    """格式化账户带宽信息"""
    address = result["address"]
    free_net_limit = result["free_net_limit"]
    free_net_used = result["free_net_used"]
    free_net_remaining = result["free_net_remaining"]
    net_limit = result["net_limit"]
    net_used = result["net_used"]
    net_remaining = result["net_remaining"]
    total_remaining = result["total_remaining"]
    
    lines = [f"🌐 地址 {address} 带宽 (Bandwidth) 资源情况："]
    
    free_pct = (free_net_used / free_net_limit * 100) if free_net_limit > 0 else 0
    lines.append(f"  免费带宽: {free_net_remaining:,} / {free_net_limit:,} (已用 {free_net_used:,}, {free_pct:.1f}%)")
    
    if net_limit > 0:
        staked_pct = (net_used / net_limit * 100) if net_limit > 0 else 0
        lines.append(f"  质押带宽: {net_remaining:,} / {net_limit:,} (已用 {net_used:,}, {staked_pct:.1f}%)")
    else:
        lines.append(f"  质押带宽: 无（未质押 TRX 获取带宽）")
    
    lines.append(f"  总可用: {total_remaining:,}")
    
    trx_transfers = total_remaining // TRX_TRANSFER_BANDWIDTH_COST if total_remaining > 0 else 0
    usdt_transfers = total_remaining // USDT_TRANSFER_BANDWIDTH_COST if total_remaining > 0 else 0
    if total_remaining > 0:
        lines.append(f"  📌 当前带宽约可执行 {trx_transfers} 笔 TRX 转账(~{TRX_TRANSFER_BANDWIDTH_COST}字节) 或 {usdt_transfers} 笔 USDT 转账(~{USDT_TRANSFER_BANDWIDTH_COST}字节)")
    
    return {**result, "summary": "\n".join(lines)}
