"""调用路由器 - 单入口 call 函数实现"""

from . import skills as skills_module
from . import tron_client
from . import tx_builder
from . import validators
from . import formatters


def _get_skills() -> dict:
    """获取技能列表（可被测试 mock）"""
    return skills_module.get_skills()


def _get_gas_parameters() -> dict:
    """获取 Gas 参数（可被测试 mock）"""
    gas_price = tron_client.get_gas_parameters()
    return formatters.format_gas_parameters(gas_price)


def _get_usdt_balance(addr: str) -> dict:
    """获取 USDT 余额（可被测试 mock）"""
    balance = tron_client.get_usdt_balance(addr)
    balance_raw = int(balance * 1_000_000)
    return formatters.format_usdt_balance(addr, balance_raw)


def _get_balance(addr: str) -> dict:
    """获取 TRX 余额（可被测试 mock）"""
    balance = tron_client.get_balance_trx(addr)
    balance_sun = int(balance * 1_000_000)
    return formatters.format_trx_balance(addr, balance_sun)


def _get_transaction_status(txid: str) -> dict:
    """获取交易状态（可被测试 mock）"""
    success, block_number = tron_client.get_transaction_status(txid)
    return formatters.format_tx_status(txid, success, block_number)


def _get_network_status() -> dict:
    """获取网络状态（可被测试 mock）"""
    block_height = tron_client.get_network_status()
    return formatters.format_network_status(block_height)


def _check_account_safety(addr: str) -> dict:
    """检查账户安全性（可被测试 mock）"""
    risk_info = tron_client.check_account_risk(addr)
    return formatters.format_account_safety(addr, risk_info)


def _build_unsigned_tx(from_addr: str, to_addr: str, amount: float, token: str = "USDT") -> dict:
    """构建未签名交易（可被测试 mock）"""
    tx_result = tx_builder.build_unsigned_tx(from_addr, to_addr, amount, token)
    
    # 提取发送方检查结果（如果有）
    sender_check = tx_result.get("sender_check")
    # 提取接收方检查结果（如果有），使用 get() 避免修改原对象
    recipient_check = tx_result.get("recipient_check")
    
    # 构建不包含 sender_check 和 recipient_check 的 unsigned_tx
    unsigned_tx = {k: v for k, v in tx_result.items() if k not in ("sender_check", "recipient_check")}
    
    # 构建基础响应
    summary = f"已生成从 {from_addr[:8]}... 到 {to_addr[:8]}... 转账 {amount} {token} 的未签名交易。"
    
    result = {
        "unsigned_tx": unsigned_tx,
        "summary": summary,
    }
    
    # 如果有发送方余额检查结果，添加到响应中
    if sender_check:
        result["sender_check"] = sender_check
    
    # 如果有接收方预警，添加到响应中
    if recipient_check and recipient_check.get("warnings"):
        result["recipient_warnings"] = recipient_check["warnings"]
        warning_msg = recipient_check.get("warning_message", "")
        if warning_msg:
            result["summary"] = summary + " " + warning_msg
    
    return result


def call(action: str, params: dict = None) -> dict:
    """
    单入口调用路由器

    Args:
        action: 动作名称
        params: 动作参数

    Returns:
        格式化的结果字典
    """
    if params is None:
        params = {}

    # 路由到具体动作
    if action == "skills":
        return _handle_skills()

    elif action == "get_usdt_balance":
        return _handle_get_usdt_balance(params)

    elif action == "get_balance":
        return _handle_get_balance(params)

    elif action == "get_gas_parameters":
        return _handle_get_gas_parameters()

    elif action == "get_transaction_status":
        return _handle_get_transaction_status(params)

    elif action == "get_network_status":
        return _handle_get_network_status()

    elif action == "get_account_status":
        return _handle_get_account_status(params)

    elif action == "check_account_safety":
        return _handle_check_account_safety(params)

    elif action == "build_tx":
        return _handle_build_tx(params)

    else:
        return _error_response(
            "unknown_action",
            f"未知的动作: {action}",
        )


def _handle_skills() -> dict:
    """处理 skills 动作 - 返回技能列表"""
    return _get_skills()


def _handle_get_usdt_balance(params: dict) -> dict:
    """处理 get_usdt_balance 动作"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")

    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")

    try:
        return _get_usdt_balance(address)
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_get_balance(params: dict) -> dict:
    """处理 get_balance 动作 (TRX)"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")

    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")

    try:
        return _get_balance(address)
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_get_gas_parameters() -> dict:
    """处理 get_gas_parameters 动作"""
    try:
        return _get_gas_parameters()
    except TimeoutError as e:
        return _error_response("timeout", f"请求超时: {e}")
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_get_transaction_status(params: dict) -> dict:
    """处理 get_transaction_status 动作"""
    txid = params.get("txid")
    if not txid:
        return _error_response("missing_param", "缺少必填参数: txid")

    if not validators.is_valid_txid(txid):
        return _error_response("invalid_txid", f"无效的交易哈希格式: {txid}")

    try:
        return _get_transaction_status(txid)
    except ValueError as e:
        if "不存在" in str(e) or "尚未确认" in str(e):
            return {
                "txid": txid,
                "status": "pending",
                "confirmed": False,
                "summary": f"交易 {txid[:16]}... 尚未确认，请稍后再查询。",
            }
        return _error_response("invalid_response", f"响应异常: {e}")
    except Exception as e:
        return _error_response("unknown", f"未知异常: {e}")


def _handle_get_network_status() -> dict:
    """处理 get_network_status 动作"""
    try:
        return _get_network_status()
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_get_account_status(params: dict) -> dict:
    """处理 get_account_status 动作 - 检查账户激活状态"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")

    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")

    try:
        account_status = tron_client.get_account_status(address)
        return formatters.format_account_status(account_status)
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_check_account_safety(params: dict) -> dict:
    """处理 check_account_safety 动作 - 检查账户是否为恶意地址"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")

    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")

    try:
        return _check_account_safety(address)
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_build_tx(params: dict) -> dict:
    """处理 build_tx 动作"""
    from_addr = params.get("from")
    to_addr = params.get("to")
    amount = params.get("amount")
    token = params.get("token", "USDT")

    # 参数校验
    if not from_addr:
        return _error_response("missing_param", "缺少必填参数: from")
    if not to_addr:
        return _error_response("missing_param", "缺少必填参数: to")
    if amount is None:
        return _error_response("missing_param", "缺少必填参数: amount")

    if not validators.is_valid_address(from_addr):
        return _error_response("invalid_address", f"无效的发送方地址: {from_addr}")
    if not validators.is_valid_address(to_addr):
        return _error_response("invalid_address", f"无效的接收方地址: {to_addr}")
    if not validators.is_positive_amount(amount):
        return _error_response("invalid_amount", f"金额必须为正数: {amount}")

    try:
        return _build_unsigned_tx(from_addr, to_addr, amount, token)
    except tx_builder.InsufficientBalanceError as e:
        # 策略二：余额不足时返回详细的错误信息，拒绝构建交易以节省 Gas
        return {
            "error": True,
            "error_type": e.error_code,
            "message": str(e),
            "details": e.details,
            "summary": str(e),
        }
    except ValueError as e:
        return _error_response("build_error", str(e))
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _error_response(error_type: str, message: str) -> dict:
    """构造错误响应"""
    return formatters.format_error(error_type, message)
