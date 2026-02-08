"""调用路由器 - 单入口 call 函数实现"""

import json
import logging

from . import skills as skills_module
from . import tron_client
from . import trongrid_client
from . import tx_builder
from . import key_manager
from . import validators
from . import formatters
from . import address_book
from .key_manager import KeyManager

logger = logging.getLogger(__name__)

# 全局 KeyManager 实例
_key_manager = KeyManager()


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
    tx_info = tron_client.get_transaction_status(txid)
    return formatters.format_tx_status(txid, tx_info)


def _get_network_status() -> dict:
    """获取网络状态（可被测试 mock）"""
    block_height = tron_client.get_network_status()
    return formatters.format_network_status(block_height)


def _check_account_safety(addr: str) -> dict:
    """检查账户安全性（可被测试 mock）"""
    risk_info = tron_client.check_account_risk(addr)
    return formatters.format_account_safety(addr, risk_info)


def _build_unsigned_tx(from_addr: str, to_addr: str, amount: float, token: str = "USDT", force_execution: bool = False) -> dict:
    """构建未签名交易（可被测试 mock）"""
    tx_result = tx_builder.build_unsigned_tx(from_addr, to_addr, amount, token, force_execution=force_execution)
    
    # 检查是否被熔断拦截
    if tx_result.get("blocked"):
        return tx_result
    
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

    # 路由到具体动作（字典映射）
    handler = _ACTION_HANDLERS.get(action)
    if handler is None:
        return _error_response(
            "unknown_action",
            f"未知的动作: {action}",
        )
    return handler(params)


def _handle_skills(params: dict) -> dict:
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


def _handle_get_gas_parameters(params: dict) -> dict:
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


def _handle_get_network_status(params: dict) -> dict:
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
    force_execution = params.get("force_execution", False)
    memo = params.get("memo", "")

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
        # 构建预览交易（不包含 memo，因为是预览）
        preview_result = _build_unsigned_tx(from_addr, to_addr, amount, token, force_execution)
        
        # 如果有 memo，需要通过 TronGrid 构建真实交易
        if memo:
            # 将 memo 转换为 hex
            memo_hex = memo.encode("utf-8").hex()
            
            token_upper = token.upper()
            amount_float = float(amount)
            
            # 通过 TronGrid 构建包含 memo 的真实交易
            if token_upper == "USDT":
                unsigned_tx = trongrid_client.build_trc20_transfer(
                    from_addr, to_addr, amount_float,
                    extra_data=memo_hex,
                )
            else:
                unsigned_tx = trongrid_client.build_trx_transfer(
                    from_addr, to_addr, amount_float,
                    extra_data=memo_hex,
                )
            
            # 替换预览结果中的 unsigned_tx
            preview_result["unsigned_tx"] = unsigned_tx
            
            # 更新 summary 添加 memo 信息
            if "summary" in preview_result:
                preview_result["summary"] = preview_result["summary"] + f" 备注: {memo}"
        
        return preview_result
        
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


def _handle_broadcast_tx(params: dict) -> dict:
    """处理 broadcast_tx 动作 — 广播已签名交易"""
    signed_tx_json = params.get("signed_tx_json")
    if not signed_tx_json:
        return _error_response("missing_param", "缺少必填参数: signed_tx_json")

    # MCP 工具间传递的是 JSON 字符串，必须先反序列化为字典
    if isinstance(signed_tx_json, dict):
        signed_tx = signed_tx_json
    else:
        try:
            signed_tx = json.loads(signed_tx_json)
        except (json.JSONDecodeError, TypeError) as e:
            return _error_response("invalid_json", f"无法解析 JSON: {e}")

    try:
        result = trongrid_client.broadcast_transaction(signed_tx)
        return formatters.format_broadcast_result(result)
    except ValueError as e:
        return _error_response("broadcast_error", str(e))
    except Exception as e:
        logger.error(f"广播失败: {e}", exc_info=True)
        return _error_response("broadcast_error", f"广播过程异常: {e}")


def _handle_transfer(params: dict) -> dict:
    """处理 transfer 动作 — 完整转账闭环：安全检查 → 构建 → 签名 → 广播"""
    to_addr = params.get("to")
    amount = params.get("amount")
    token = params.get("token", "USDT")
    force_execution = params.get("force_execution", False)
    memo = params.get("memo", "")

    if not to_addr:
        return _error_response("missing_param", "缺少必填参数: to")
    if amount is None:
        return _error_response("missing_param", "缺少必填参数: amount")
    if not validators.is_valid_address(to_addr):
        return _error_response("invalid_address", f"无效的接收方地址: {to_addr}")
    if not validators.is_positive_amount(amount):
        return _error_response("invalid_amount", f"金额必须为正数: {amount}")

    try:
        # 1. 加载私钥，派生钱包地址
        pk = key_manager.load_private_key()
        from_addr = key_manager.get_address_from_private_key(pk)
    except ValueError as e:
        return _error_response("wallet_error", str(e))

    token_upper = token.upper()
    if token_upper not in ("USDT", "TRX"):
        return _error_response("invalid_token", f"不支持的代币类型: {token}")

    amount_float = float(amount)

    # 2. 安全检查（复用 tx_builder 的全部检查逻辑）
    try:
        preview = tx_builder.build_unsigned_tx(
            from_addr, to_addr, amount_float, token_upper,
            force_execution=force_execution,
        )
        # 如果被熔断拦截
        if preview.get("blocked"):
            return preview
    except tx_builder.InsufficientBalanceError as e:
        return {
            "error": True,
            "error_type": e.error_code,
            "message": str(e),
            "details": e.details,
            "summary": str(e),
        }
    except ValueError as e:
        return _error_response("validation_error", str(e))

    # 3. 通过 TronGrid 构建真实交易
    try:
        # 将 memo 转换为 hex
        memo_hex = memo.encode("utf-8").hex() if memo else ""
        
        if token_upper == "USDT":
            unsigned_tx = trongrid_client.build_trc20_transfer(
                from_addr, to_addr, amount_float,
                extra_data=memo_hex if memo_hex else None,
            )
        else:
            unsigned_tx = trongrid_client.build_trx_transfer(
                from_addr, to_addr, amount_float,
                extra_data=memo_hex if memo_hex else None,
            )
    except Exception as e:
        return _error_response("build_error", f"TronGrid 构建交易失败: {e}")

    # 4. 签名
    try:
        tx_id = unsigned_tx["txID"]
        signature = key_manager.sign_transaction(tx_id, pk)
        signed_tx = dict(unsigned_tx)
        signed_tx["signature"] = [signature]
    except Exception as e:
        return _error_response("sign_error", f"签名失败: {e}")

    # 5. 广播
    try:
        broadcast_result = trongrid_client.broadcast_transaction(signed_tx)
    except Exception as e:
        return _error_response("broadcast_error", f"广播失败: {e}")

    # 6. 返回完整结果
    return formatters.format_transfer_result(
        broadcast_result, from_addr, to_addr, amount_float, token_upper,
        security_check=preview.get("security_check"),
        recipient_check=preview.get("recipient_check"),
    )


def _handle_get_wallet_info(params: dict) -> dict:
    """处理 get_wallet_info 动作 — 查看钱包信息"""
    try:
        pk = key_manager.load_private_key()
        address = key_manager.get_address_from_private_key(pk)
    except ValueError as e:
        return _error_response("wallet_error", str(e))

    # 查询余额
    trx_balance = 0.0
    usdt_balance = 0.0
    try:
        trx_balance = tron_client.get_balance_trx(address)
    except Exception as e:
        logger.warning(f"查询钱包 TRX 余额失败: {e}")
    try:
        usdt_balance = tron_client.get_usdt_balance(address)
    except Exception as e:
        logger.warning(f"查询钱包 USDT 余额失败: {e}")

    return formatters.format_wallet_info(address, trx_balance, usdt_balance)


def _handle_get_transaction_history(params: dict) -> dict:
    """处理 get_transaction_history 动作 — 查询交易历史记录"""
    address = params.get("address")
    limit = params.get("limit", 10)
    start = params.get("start", 0)
    token = params.get("token")

    # 参数校验
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")
    
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")
    
    # 转换并校验 limit
    try:
        limit = int(limit)
        if limit < 1 or limit > 50:
            return _error_response("invalid_param", f"limit 必须在 1-50 范围内，当前值: {limit}")
    except (ValueError, TypeError):
        return _error_response("invalid_param", "limit 必须为整数")
    
    # 转换并校验 start
    try:
        start = int(start)
        if start < 0:
            start = 0
    except (ValueError, TypeError):
        return _error_response("invalid_param", "start 必须为非负整数")

    try:
        # 根据 token 参数决定查询策略
        if token is None:
            # 不筛选代币，合并 TRX/TRC10 和 TRC20 交易记录
            try:
                # 获取 TRX/TRC10 转账记录
                trx_data = tron_client.get_transfer_history(address, limit, start)
                trx_transfers = trx_data.get("data", [])
                trx_total = trx_data.get("total", 0)
            except Exception as e:
                logger.warning(f"获取 TRX/TRC10 转账记录失败: {e}")
                trx_transfers = []
                trx_total = 0
            
            try:
                # 获取 TRC20 转账记录
                trc20_data = tron_client.get_trc20_transfer_history(address, limit, start)
                trc20_transfers = trc20_data.get("token_transfers", trc20_data.get("data", []))
                trc20_total = trc20_data.get("total", 0)
            except Exception as e:
                logger.warning(f"获取 TRC20 转账记录失败: {e}")
                trc20_transfers = []
                trc20_total = 0
            
            # 合并两种类型的交易记录
            all_transfers = trx_transfers + trc20_transfers
            
            # 按 timestamp 降序排序
            all_transfers.sort(
                key=lambda x: x.get("timestamp", x.get("block_ts", 0)),
                reverse=True
            )
            
            # 取前 limit 条
            all_transfers = all_transfers[:limit]
            
            # 总数取两者之和（近似值，注意：可能存在重复计数）
            # 警告：如果某些交易同时出现在两个 API 结果中，total 可能不准确
            total = trx_total + trc20_total
            
            return formatters.format_transaction_history(
                address, all_transfers, total, token, limit
            )
        
        elif token.upper() == "USDT":
            # 查询 USDT (TRC20) 转账记录
            data = tron_client.get_trc20_transfer_history(
                address, limit, start, contract_address=tron_client.USDT_CONTRACT_BASE58
            )
            transfers = data.get("token_transfers", data.get("data", []))
            total = data.get("total", 0)
            return formatters.format_transaction_history(
                address, transfers, total, "USDT", limit
            )
        
        elif token.upper() == "TRX":
            # 查询 TRX 转账记录
            data = tron_client.get_transfer_history(address, limit, start, token="_")
            transfers = data.get("data", [])
            total = data.get("total", 0)
            return formatters.format_transaction_history(
                address, transfers, total, "TRX", limit
            )
        
        elif token.startswith("T") and len(token) == 34:
            # TRC20 合约地址（以 T 开头的 34 位地址）
            data = tron_client.get_trc20_transfer_history(
                address, limit, start, contract_address=token
            )
            transfers = data.get("token_transfers", data.get("data", []))
            total = data.get("total", 0)
            return formatters.format_transaction_history(
                address, transfers, total, token, limit
            )
        
        else:
            # 其他代币名称（TRC10 token name）
            data = tron_client.get_transfer_history(address, limit, start, token=token)
            transfers = data.get("data", [])
            total = data.get("total", 0)
            return formatters.format_transaction_history(
                address, transfers, total, token, limit
            )
    
    except Exception as e:
        logger.error(f"查询交易历史失败: {e}", exc_info=True)
        return _error_response("rpc_error", f"查询失败: {e}")


def _handle_sign_tx(params: dict) -> dict:
    """处理 sign_tx 动作 — 对未签名交易进行本地签名"""
    unsigned_tx_json = params.get("unsigned_tx_json")
    
    # 参数校验
    if not unsigned_tx_json:
        return _error_response("missing_param", "缺少必填参数: unsigned_tx_json")
    
    # 支持 dict 和 JSON 字符串两种输入
    if isinstance(unsigned_tx_json, dict):
        unsigned_tx = unsigned_tx_json
    else:
        try:
            unsigned_tx = json.loads(unsigned_tx_json)
        except (json.JSONDecodeError, TypeError) as e:
            return _error_response("invalid_json", f"无法解析 JSON: {e}")
    
    # 校验交易必须包含 txID 和 raw_data 字段
    if "txID" not in unsigned_tx:
        return _error_response("invalid_tx", "交易缺少 txID 字段")
    
    if "raw_data" not in unsigned_tx:
        return _error_response("invalid_tx", "交易缺少 raw_data 字段")
    
    # 加载私钥并签名
    try:
        pk = key_manager.load_private_key()
        tx_id = unsigned_tx["txID"]
        signature = key_manager.sign_transaction(tx_id, pk)
        
        # 构建签名后的交易
        signed_tx = dict(unsigned_tx)
        signed_tx["signature"] = [signature]
        
        # 使用 formatters.format_signed_tx 格式化返回
        # 需要提取发送方和接收方地址（如果有的话）
        from_addr = ""
        to_addr = ""
        amount = 0.0
        token = ""
        
        # 尝试从 raw_data 中提取信息（可选）
        raw_data = unsigned_tx.get("raw_data", {})
        contracts = raw_data.get("contract", [])
        if contracts:
            contract = contracts[0]
            parameter = contract.get("parameter", {})
            value = parameter.get("value", {})
            from_addr = value.get("owner_address", "")
            to_addr = value.get("to_address", "") or value.get("contract_address", "")
            amount_raw = value.get("amount", 0)
            # 尝试推断代币类型
            if contract.get("type") == "TransferContract":
                token = "TRX"
                amount = amount_raw / 1_000_000
            elif contract.get("type") == "TriggerSmartContract":
                token = "TRC20"
                amount = amount_raw / 1_000_000  # 假设 6 位小数
        
        return formatters.format_signed_tx(signed_tx, from_addr, to_addr, amount, token)
        
    except ValueError as e:
        return _error_response("sign_error", str(e))
    except Exception as e:
        logger.error(f"签名失败: {e}", exc_info=True)
        return _error_response("sign_error", f"签名过程异常: {e}")


def _handle_get_internal_transactions(params: dict) -> dict:
    """处理 get_internal_transactions 动作 — 查询内部交易"""
    address = params.get("address")
    limit = params.get("limit", 20)
    start = params.get("start", 0)
    
    # 参数校验
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")
    
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")
    
    # 转换并校验 limit
    try:
        limit = int(limit)
        if limit < 1 or limit > 50:
            return _error_response("invalid_param", f"limit 必须在 1-50 范围内，当前值: {limit}")
    except (ValueError, TypeError):
        return _error_response("invalid_param", "limit 必须为整数")
    
    # 转换并校验 start
    try:
        start = int(start)
        if start < 0:
            start = 0
    except (ValueError, TypeError):
        return _error_response("invalid_param", "start 必须为非负整数")
    
    try:
        # 查询内部交易
        data = tron_client.get_internal_transactions(address, limit, start)
        internal_txs = data.get("data", [])
        total = data.get("total", 0)
        
        # 格式化返回
        return formatters.format_internal_transactions(address, internal_txs, total, limit)
    
    except Exception as e:
        logger.error(f"查询内部交易失败: {e}", exc_info=True)
        return _error_response("rpc_error", f"查询失败: {e}")


def _handle_get_account_tokens(params: dict) -> dict:
    """处理 get_account_tokens 动作 — 查询账户持有的所有代币"""
    address = params.get("address")
    
    # 参数校验
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")
    
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")
    
    try:
        # 查询代币列表
        result = tron_client.get_account_tokens(address)
        
        # 格式化返回
        return formatters.format_account_tokens(
            result["address"],
            result["tokens"],
            result["token_count"]
        )
    
    except Exception as e:
        logger.error(f"查询账户代币失败: {e}", exc_info=True)
        return _error_response("rpc_error", f"查询失败: {e}")


def _handle_addressbook_add(params: dict) -> dict:
    """处理 addressbook_add 动作 — 添加联系人"""
    alias = params.get("alias")
    address = params.get("address")
    note = params.get("note", "")

    if not alias:
        return _error_response("missing_param", "缺少必填参数: alias（联系人别名）")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address（TRON 地址）")
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")

    try:
        result = address_book.add_contact(alias, address, note)
        return formatters.format_addressbook_add(result)
    except Exception as e:
        return _error_response("addressbook_error", f"添加联系人失败: {e}")


def _handle_addressbook_remove(params: dict) -> dict:
    """处理 addressbook_remove 动作 — 删除联系人"""
    alias = params.get("alias")
    if not alias:
        return _error_response("missing_param", "缺少必填参数: alias（联系人别名）")

    try:
        result = address_book.remove_contact(alias)
        return formatters.format_addressbook_remove(result)
    except Exception as e:
        return _error_response("addressbook_error", f"删除联系人失败: {e}")


def _handle_addressbook_lookup(params: dict) -> dict:
    """处理 addressbook_lookup 动作 — 查找联系人"""
    alias = params.get("alias")
    if not alias:
        return _error_response("missing_param", "缺少必填参数: alias（联系人别名）")

    try:
        result = address_book.lookup(alias)
        return formatters.format_addressbook_lookup(result)
    except Exception as e:
        return _error_response("addressbook_error", f"查找联系人失败: {e}")


def _handle_addressbook_list(params: dict) -> dict:
    """处理 addressbook_list 动作 — 列出所有联系人"""
    try:
        result = address_book.list_contacts()
        return formatters.format_addressbook_list(result)
    except Exception as e:
        return _error_response("addressbook_error", f"获取地址簿失败: {e}")


def _handle_get_account_energy(params: dict) -> dict:
    """处理 get_account_energy 动作 — 查询账户能量"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")
    
    try:
        result = tron_client.get_account_energy(address)
        return formatters.format_account_energy(result)
    except Exception as e:
        return _error_response("rpc_error", str(e))


def _handle_get_account_bandwidth(params: dict) -> dict:
    """处理 get_account_bandwidth 动作 — 查询账户带宽"""
    address = params.get("address")
    if not address:
        return _error_response("missing_param", "缺少必填参数: address")
    if not validators.is_valid_address(address):
        return _error_response("invalid_address", f"无效的地址格式: {address}")
    
    try:
        result = tron_client.get_account_bandwidth(address)
        return formatters.format_account_bandwidth(result)
    except Exception as e:
        return _error_response("rpc_error", str(e))


# 动作路由表 — 字典映射提升可维护性
_ACTION_HANDLERS = {
    "skills": _handle_skills,
    "get_usdt_balance": _handle_get_usdt_balance,
    "get_balance": _handle_get_balance,
    "get_gas_parameters": _handle_get_gas_parameters,
    "get_transaction_status": _handle_get_transaction_status,
    "get_network_status": _handle_get_network_status,
    "get_account_status": _handle_get_account_status,
    "check_account_safety": _handle_check_account_safety,
    "build_tx": _handle_build_tx,
    "sign_tx": _handle_sign_tx,
    "broadcast_tx": _handle_broadcast_tx,
    "transfer": _handle_transfer,
    "get_wallet_info": _handle_get_wallet_info,
    "get_transaction_history": _handle_get_transaction_history,
    "get_internal_transactions": _handle_get_internal_transactions,
    "get_account_tokens": _handle_get_account_tokens,
    "addressbook_add": _handle_addressbook_add,
    "addressbook_remove": _handle_addressbook_remove,
    "addressbook_lookup": _handle_addressbook_lookup,
    "addressbook_list": _handle_addressbook_list,
    "get_account_energy": _handle_get_account_energy,
    "get_account_bandwidth": _handle_get_account_bandwidth,
}


def _error_response(error_type: str, message: str) -> dict:
    """构造错误响应"""
    return formatters.format_error(error_type, message)
