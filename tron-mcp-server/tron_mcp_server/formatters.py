"""格式化模块 - 结构化输出 + 自然语言摘要"""

import json


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
    txid: str, success: bool, block_number: int, confirmations: int = 0
) -> dict:
    """格式化交易状态"""
    status = "成功" if success else "失败"
    return {
        "txid": txid,
        "status": status,
        "success": success,
        "block_number": block_number,
        "confirmations": confirmations,
        "summary": f"交易 {txid[:16]}... 状态：{status}，所在区块 {block_number:,}，已确认 {confirmations} 次。",
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
    is_unknown = risk_type in ("Unknown", "Partially Verified")
    is_safe = not is_risky and not is_unknown
    
    if is_unknown:
        safety_status = "无法验证"
    elif is_safe:
        safety_status = "安全"
    else:
        safety_status = f"危险（{risk_type}）"
    
    # 构建摘要
    if is_unknown:
        summary = f"地址 {address} 安全检查完成：⚠️ 无法获取风险信息，请谨慎操作。"
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
    
    for tx in transfers:
        # 提取交易哈希
        txid = tx.get("transactionHash") or tx.get("transaction_id") or ""
        
        # 提取发送方和接收方地址
        from_addr = tx.get("transferFromAddress") or tx.get("from_address") or tx.get("from") or ""
        to_addr = tx.get("transferToAddress") or tx.get("to_address") or tx.get("to") or ""
        
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
            if from_addr == address:
                if to_addr == address:
                    direction = "SELF"
                else:
                    direction = "OUT"
            elif to_addr == address:
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
        f"地址 {address} 共有 {total} 笔交易记录{filter_text}，"
        f"当前显示最近 {len(formatted_transfers)} 笔。"
    )
    
    return {
        "address": address,
        "total": total,
        "displayed": len(formatted_transfers),
        "token_filter": token_filter,
        "transfers": formatted_transfers,
        "summary": summary,
    }


def format_account_resources(address: str, resources: dict) -> dict:
    """
    格式化账户资源信息

    将 TronGrid 的 getaccountresource 响应转化为人类可读格式，
    并计算剩余量和使用百分比。
    """
    # 免费带宽
    free_net_used = resources.get("freeNetUsed", 0)
    free_net_limit = resources.get("freeNetLimit", 600)  # 默认免费 600
    free_net_remaining = max(0, free_net_limit - free_net_used)

    # 质押带宽
    net_used = resources.get("NetUsed", 0)
    net_limit = resources.get("NetLimit", 0)
    net_remaining = max(0, net_limit - net_used)

    # 能量
    energy_used = resources.get("EnergyUsed", 0)
    energy_limit = resources.get("EnergyLimit", 0)
    energy_remaining = max(0, energy_limit - energy_used)

    # 全网权重（用于计算质押多少 TRX 可获得多少 Energy）
    total_energy_limit = resources.get("TotalEnergyLimit", 90_000_000_000)
    total_energy_weight = resources.get("TotalEnergyWeight", 0)
    total_net_limit = resources.get("TotalNetLimit", 43_200_000_000)
    total_net_weight = resources.get("TotalNetWeight", 0)

    # TronPower
    tron_power_used = resources.get("tronPowerUsed", 0)
    tron_power_limit = resources.get("tronPowerLimit", 0)

    # 构建摘要
    summary_parts = [f"地址 {address} 资源概况："]
    summary_parts.append(
        f"⚡ Energy: {energy_remaining:,}/{energy_limit:,}"
        f"（已用 {energy_used:,}）"
    )
    summary_parts.append(
        f"🌐 带宽: 免费 {free_net_remaining}/{free_net_limit}"
        f"，质押 {net_remaining:,}/{net_limit:,}"
    )

    if energy_limit == 0:
        summary_parts.append(
            "💡 提示：您没有任何 Energy，TRC20 转账将直接消耗 TRX。"
            "建议质押 TRX 获取 Energy 以降低交易成本。"
        )

    return {
        "address": address,
        "energy": {
            "used": energy_used,
            "limit": energy_limit,
            "remaining": energy_remaining,
        },
        "bandwidth": {
            "free_used": free_net_used,
            "free_limit": free_net_limit,
            "free_remaining": free_net_remaining,
            "staked_used": net_used,
            "staked_limit": net_limit,
            "staked_remaining": net_remaining,
        },
        "tron_power": {
            "used": tron_power_used,
            "limit": tron_power_limit,
        },
        "network": {
            "total_energy_limit": total_energy_limit,
            "total_energy_weight": total_energy_weight,
            "total_net_limit": total_net_limit,
            "total_net_weight": total_net_weight,
        },
        "summary": " ".join(summary_parts),
    }
