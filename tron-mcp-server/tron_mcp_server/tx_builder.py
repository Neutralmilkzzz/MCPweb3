"""交易构建模块 - 构造未签名交易"""

import logging
import os
import time
import hashlib
import base58
from . import tron_client
from . import validators


# SUN 与 TRX 的转换倍数 (1 TRX = 1,000,000 SUN)
SUN_PER_TRX = 1_000_000

# USDT TRC20 合约地址
# Default to Mainnet if not set
USDT_CONTRACT = os.getenv("USDT_CONTRACT_ADDRESS", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")

# 交易过期时间（毫秒）
TX_EXPIRATION_MS = 10 * 60 * 1000


def _timestamp_ms() -> int:
    """获取当前时间戳（毫秒）"""
    return int(time.time() * 1000)


def _get_ref_block() -> tuple:
    """
    获取参考区块信息
    返回 (ref_block_bytes, ref_block_hash)
    """
    block_info = tron_client.get_latest_block_info()
    block_num = block_info["number"]
    block_hash = block_info["hash"]
    
    ref_block_bytes = hex(block_num & 0xFFFF)[2:].zfill(4)
    ref_block_hash = block_hash[16:32] if len(block_hash) >= 32 else block_hash[:8]
    
    return (ref_block_bytes, ref_block_hash)


def _encode_transfer(to: str, amount: int) -> str:
    """
    编码 TRC20 transfer 函数调用
    
    Args:
        to: 接收方 TRON 地址 (Base58Check 格式, 以 'T' 开头)
        amount: 转账金额 (最小单位)
    
    Returns:
        编码后的函数调用数据 (method signature + address + amount)
    
    Raises:
        ValueError: 地址格式无效时抛出
    """
    method_sig = "a9059cbb"
    
    # 1. Base58Check 解码 -> Hex
    try:
        raw_bytes = base58.b58decode_check(to)
    except ValueError as e:
        raise ValueError(f"无效的 TRON 地址格式: {to}") from e
    
    hex_addr = raw_bytes.hex()
    
    # 2. 去掉 '41' 前缀 (TRON 主网地址前缀)
    # TRON 地址解码后必须以 '41' 开头
    if not hex_addr.startswith('41'):
        raise ValueError(f"无效的 TRON 地址: 缺少 41 前缀")
    hex_addr = hex_addr[2:]
    
    # 3. 补齐到 64 字符 (32字节, EVM/TVM 标准)
    addr_hex = hex_addr.zfill(64)
    
    amount_hex = hex(amount)[2:].zfill(64)
    return method_sig + addr_hex + amount_hex


def _trigger_smart_contract(to: str, amount: float, from_addr: str, token: str) -> dict:
    """构建 TRC20 转账交易"""
    timestamp = _timestamp_ms()
    ref_block_bytes, ref_block_hash = _get_ref_block()
    amount_raw = int(amount * SUN_PER_TRX)
    
    raw_data = {
        "contract": [
            {
                "parameter": {
                    "value": {
                        "data": _encode_transfer(to, amount_raw),
                        "owner_address": from_addr,
                        "contract_address": USDT_CONTRACT,
                    },
                    "type_url": "type.googleapis.com/protocol.TriggerSmartContract",
                },
                "type": "TriggerSmartContract",
            }
        ],
        "ref_block_bytes": ref_block_bytes,
        "ref_block_hash": ref_block_hash,
        "expiration": timestamp + TX_EXPIRATION_MS,
        "timestamp": timestamp,
    }
    
    tx_id = hashlib.sha256(str(raw_data).encode()).hexdigest()
    return {"txID": tx_id, "raw_data": raw_data}


def _build_trx_transfer(from_addr: str, to_addr: str, amount: float) -> dict:
    """构建 TRX 原生转账交易"""
    timestamp = _timestamp_ms()
    ref_block_bytes, ref_block_hash = _get_ref_block()
    amount_sun = int(amount * SUN_PER_TRX)
    
    raw_data = {
        "contract": [
            {
                "parameter": {
                    "value": {
                        "amount": amount_sun,
                        "owner_address": from_addr,
                        "to_address": to_addr,
                    },
                    "type_url": "type.googleapis.com/protocol.TransferContract",
                },
                "type": "TransferContract",
            }
        ],
        "ref_block_bytes": ref_block_bytes,
        "ref_block_hash": ref_block_hash,
        "expiration": timestamp + TX_EXPIRATION_MS,
        "timestamp": timestamp,
    }
    
    tx_id = hashlib.sha256(str(raw_data).encode()).hexdigest()
    return {"txID": tx_id, "raw_data": raw_data}


# TRC20 转账预估能量消耗（SUN 单位）
# 激活账户约 29,000 Energy，未激活账户约 65,000 Energy
# 保守估计使用较高值
ESTIMATED_USDT_ENERGY = int(os.getenv("ESTIMATED_USDT_ENERGY", "65000"))
# 每单位 Energy 的 SUN 价格（默认 420 SUN）
ENERGY_PRICE_SUN = int(os.getenv("ENERGY_PRICE_SUN", "420"))
# TRX 转账最小 Gas 费用（SUN 单位，约 0.1 TRX = 100,000 SUN）
MIN_TRX_TRANSFER_FEE = int(os.getenv("MIN_TRX_TRANSFER_FEE", "100000"))


class InsufficientBalanceError(ValueError):
    """余额不足异常，用于在交易构建前拦截必死交易"""
    
    def __init__(self, message: str, error_code: str, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details or {}


def check_sender_balance(
    from_address: str,
    amount: float,
    token: str,
) -> dict:
    """
    检查发送方余额是否充足，拦截必死交易
    
    这是策略二的核心实现：在本地（Builder 阶段）拦截余额不足的交易，
    避免这些交易上链后失败导致 Gas 浪费。
    
    Args:
        from_address: 发送方地址
        amount: 转账金额
        token: 代币类型 (USDT 或 TRX)
    
    Returns:
        包含检查结果的字典:
        - checked: 是否成功完成检查
        - sufficient: 余额是否充足
        - errors: 错误列表（如果余额不足）
        - balances: 当前余额信息
    
    Raises:
        InsufficientBalanceError: 余额明确不足时抛出，阻止交易构建
    """
    token_upper = token.upper()
    errors = []
    
    try:
        # 获取发送方 TRX 余额
        trx_balance = tron_client.get_balance_trx(from_address)
        trx_balance_sun = int(trx_balance * SUN_PER_TRX)
    except Exception as e:
        logging.warning(f"检查发送方 TRX 余额失败 ({from_address}): {e}")
        # 如果无法查询余额，不阻止交易（保守策略）
        return {
            "checked": False,
            "sufficient": None,
            "errors": [],
            "error_message": None,
            "balances": None,
        }
    
    if token_upper == "USDT":
        # USDT 转账检查
        try:
            usdt_balance = tron_client.get_usdt_balance(from_address)
        except Exception as e:
            logging.warning(f"检查发送方 USDT 余额失败 ({from_address}): {e}")
            return {
                "checked": False,
                "sufficient": None,
                "errors": [],
                "error_message": None,
                "balances": {"trx": trx_balance},
            }
        
        # 检查 USDT 余额是否充足
        if usdt_balance < amount:
            errors.append({
                "code": "insufficient_usdt",
                "message": f"USDT 余额不足: 需要 {amount} USDT，当前余额 {usdt_balance} USDT",
                "severity": "error",
                "required": amount,
                "available": usdt_balance,
            })
        
        # 检查 TRX 是否足够支付 Gas（Energy 费用）
        estimated_fee_sun = ESTIMATED_USDT_ENERGY * ENERGY_PRICE_SUN
        estimated_fee_trx = estimated_fee_sun / SUN_PER_TRX
        
        if trx_balance_sun < estimated_fee_sun:
            errors.append({
                "code": "insufficient_trx_for_gas",
                "message": f"TRX 余额不足以支付 Gas: 预估需要 {estimated_fee_trx:.2f} TRX，当前余额 {trx_balance:.6f} TRX",
                "severity": "error",
                "required_sun": estimated_fee_sun,
                "available_sun": trx_balance_sun,
            })
        
        balances = {
            "usdt": usdt_balance,
            "trx": trx_balance,
            "trx_sun": trx_balance_sun,
        }
    
    else:
        # TRX 转账检查
        amount_sun = int(amount * SUN_PER_TRX)
        # TRX 转账需要的总金额 = 转账金额 + Gas 费用
        total_required_sun = amount_sun + MIN_TRX_TRANSFER_FEE
        
        if trx_balance_sun < total_required_sun:
            errors.append({
                "code": "insufficient_trx",
                "message": f"TRX 余额不足: 需要 {amount} TRX + {MIN_TRX_TRANSFER_FEE / SUN_PER_TRX:.2f} TRX (Gas)，当前余额 {trx_balance:.6f} TRX",
                "severity": "error",
                "required_sun": total_required_sun,
                "available_sun": trx_balance_sun,
            })
        
        balances = {
            "trx": trx_balance,
            "trx_sun": trx_balance_sun,
        }
    
    # 如果有错误，抛出异常阻止交易构建
    if errors:
        error_messages = [e["message"] for e in errors]
        error_message = "❌ 交易拒绝: " + "; ".join(error_messages)
        
        raise InsufficientBalanceError(
            message=error_message,
            error_code=errors[0]["code"],
            details={
                "errors": errors,
                "balances": balances,
            }
        )
    
    return {
        "checked": True,
        "sufficient": True,
        "errors": [],
        "error_message": None,
        "balances": balances,
    }


def check_recipient_status(to_address: str) -> dict:
    """
    检查接收方账户状态，返回预警信息
    
    用于检测：
    1. 向未激活地址转账 TRC20 会消耗更多 Energy（SSTORE 指令）
    2. 如果接收方没有 TRX，可能无法转出收到的代币
    
    Returns:
        包含预警信息的字典
    """
    try:
        account_status = tron_client.get_account_status(to_address)
    except Exception as e:
        # 如果查询失败，记录错误信息并返回未知状态，不阻止交易
        logging.warning(f"检查接收方账户状态失败 ({to_address}): {e}")
        return {
            "checked": False,
            "warnings": [],
            "warning_message": None,
        }
    
    warnings = []
    
    # 检查账户是否未激活
    # 默认为 False (未激活)，保守处理：如果无法确定状态，假设未激活
    if not account_status.get("is_activated", False):
        warnings.append({
            "code": "unactivated_recipient",
            "message": "接收方账户未激活，转账 TRC20 将消耗更多 Energy（约 65000 额外能量）",
            "severity": "warning",
        })
    
    # 检查接收方是否没有 TRX
    # 默认为 False (没有 TRX)，保守处理：如果无法确定状态，假设没有 TRX
    if not account_status.get("has_trx", False):
        warnings.append({
            "code": "no_trx_balance",
            "message": "接收方账户没有 TRX，可能无法转出收到的代币（需要 TRX 支付手续费）",
            "severity": "warning",
        })
    
    # 构建综合警告消息
    warning_message = None
    if warnings:
        messages = [w["message"] for w in warnings]
        warning_message = "⚠️ 预警: " + "; ".join(messages)
    
    return {
        "checked": True,
        "account_status": account_status,
        "warnings": warnings,
        "warning_message": warning_message,
    }


def check_recipient_security(to_address: str) -> dict:
    """
    检查接收方地址是否被 TRONSCAN 标记为恶意地址
    
    这是 Phase 2 安全性开发的核心功能：
    集成 TRONSCAN 官方黑名单数据，识别恶意地址（如诈骗、钓鱼等）
    
    Args:
        to_address: 接收方 TRON 地址
    
    Returns:
        包含安全检查结果的字典:
        - checked: 是否成功完成检查
        - is_risky: 地址是否被标记为恶意
        - risk_type: 风险类型
        - security_warning: 高优先级安全警告 (仅当 is_risky=True)
    """
    try:
        risk_info = tron_client.check_account_risk(to_address)
    except Exception as e:
        logging.warning(f"安全检查失败 ({to_address}): {e}")
        return {
            "checked": False,
            "is_risky": False,
            "risk_type": "Unknown",
            "security_warning": None,
        }
    
    is_risky = risk_info.get("is_risky", False)
    risk_type = risk_info.get("risk_type", "Unknown")
    
    # Sanitize risk_type to prevent injection of unexpected content
    # Only allow alphanumeric characters, spaces, and common punctuation
    sanitized_risk_type = "".join(
        c for c in str(risk_type)[:50] if c.isalnum() or c in " -_"
    ).strip() or "Unknown"
    
    security_warning = None
    if is_risky:
        security_warning = f"⛔ 严重安全警告: 接收方地址被 TRONSCAN 标记为 【{sanitized_risk_type}】。转账极可能导致资产丢失！"
    
    return {
        "checked": True,
        "is_risky": is_risky,
        "risk_type": sanitized_risk_type,
        "detail": risk_info.get("detail"),
        "security_warning": security_warning,
    }


def build_unsigned_tx(
    from_address: str,
    to_address: str,
    amount: float,
    token: str = "USDT",
    check_recipient: bool = True,
    check_balance: bool = True,
    check_security: bool = True,
) -> dict:
    """
    构建未签名交易

    Args:
        from_address: 发送方地址
        to_address: 接收方地址
        amount: 转账金额
        token: 代币类型 (USDT 或 TRX)
        check_recipient: 是否检查接收方账户状态 (默认 True)
        check_balance: 是否预先检查发送方余额 (默认 True)
            启用后会在构建交易前检查余额，拒绝必死交易以节省 Gas
        check_security: 是否检查接收方地址安全性 (默认 True)
            启用后会检查接收方是否在 TRONSCAN 黑名单中

    Returns:
        TRON 标准未签名交易结构 (txID + raw_data)
        如果是 TRC20 转账且 check_recipient=True，还会包含接收方账户预警信息
        如果 check_balance=True，还会包含发送方余额检查结果
        如果 check_security=True 且接收方为恶意地址，还会包含 security_warning

    Raises:
        ValueError: 参数无效时抛出
        InsufficientBalanceError: 发送方余额不足时抛出（当 check_balance=True）
    """
    if not validators.is_positive_amount(amount):
        raise ValueError(f"金额必须为正数: {amount}")

    token_upper = token.upper()
    if token_upper not in ("USDT", "TRX"):
        raise ValueError(f"不支持的代币类型: {token}")

    # Phase 2: 安全性检查 - 检查接收方地址是否被标记为恶意
    security_check = None
    if check_security:
        security_check = check_recipient_security(to_address)

    # 策略二：预先检查发送方余额，拒绝必死交易
    # 在 Builder 阶段拦截余额不足的交易是 0 成本的
    sender_check = None
    if check_balance:
        # 如果余额不足，check_sender_balance 会抛出 InsufficientBalanceError
        sender_check = check_sender_balance(from_address, amount, token_upper)

    # 对于 TRC20 转账，检查接收方账户状态
    recipient_check = None
    if token_upper == "USDT" and check_recipient:
        recipient_check = check_recipient_status(to_address)

    if token_upper == "USDT":
        result = _trigger_smart_contract(to_address, amount, from_address, token_upper)
    else:
        result = _build_trx_transfer(from_address, to_address, amount)
    
    # 将安全检查结果添加到返回值
    if security_check:
        result["security_check"] = security_check
        # 如果检测到恶意地址，添加高优先级警告到顶层
        if security_check.get("security_warning"):
            result["security_warning"] = security_check["security_warning"]
    
    # 将发送方余额检查结果添加到返回值
    if sender_check:
        result["sender_check"] = sender_check
    
    # 将接收方检查结果添加到返回值
    if recipient_check:
        result["recipient_check"] = recipient_check
    
    return result
