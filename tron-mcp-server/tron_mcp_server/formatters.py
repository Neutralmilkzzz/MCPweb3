"""格式化模块 - 结构化输出 + 自然语言摘要"""


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
    is_safe = not is_risky
    safety_status = "安全" if is_safe else f"危险（{risk_type}）"
    
    # 构建摘要
    if is_safe:
        if risk_type == "Unknown":
            summary = f"地址 {address} 安全检查完成：⚠️ 无法获取风险信息，请谨慎操作。"
        elif tags.get("Blue"):
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
