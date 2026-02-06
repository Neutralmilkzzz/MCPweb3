---
name: tron-blockchain
description: 与 TRON 区块链交互的技能。通过 tron_* 系列工具直接调用。用于查询 USDT/TRX 余额、获取 Gas 参数、检查交易状态、构建未签名交易、安全检查、转账等。
---

# TRON 区块链操作技能

## 概述

此技能使你能够与 TRON 区块链进行交互，完成常见的链上操作任务。所有工具都通过 `tron_*` 系列命名，可以直接调用。

**关键词**: TRON, TRX, USDT, TRC20, 余额查询, Gas, 交易状态, 转账, 区块链, 安全检查

---

## 可用工具

此技能通过 `tron-mcp-server` MCP 服务器提供以下工具：

### 1. `tron_get_usdt_balance`
查询指定地址的 USDT (TRC20) 余额。

**参数:**
- `address` (必填): TRON 地址，支持两种格式：
  - Base58: 以 `T` 开头，34 字符（如 `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t`）
  - Hex: 以 `0x41` 开头，44 字符

**返回:**
- `address`: 查询地址
- `balance_usdt`: USDT 余额（浮点数，6 位小数）
- `balance_raw`: 原始余额（最小单位）
- `summary`: 人类可读的摘要

**示例:**
```
查询 TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t 的 USDT 余额
→ 返回: "地址 TR7N... 当前 USDT 余额为 1,234.567890 USDT。"
```

---

### 2. `tron_get_balance`
查询指定地址的 TRX 原生代币余额。

**参数:**
- `address` (必填): TRON 地址

**返回:**
- `address`: 查询地址
- `balance_trx`: TRX 余额
- `balance_sun`: SUN 单位余额（1 TRX = 1,000,000 SUN）
- `summary`: 人类可读的摘要

---

### 3. `tron_get_gas_parameters`
获取当前网络的 Gas/能量价格参数。

**参数:** 无

**返回:**
- `gas_price_sun`: Gas 价格（SUN）
- `gas_price_trx`: Gas 价格（TRX）
- `summary`: 人类可读的摘要

**使用场景:**
- 在构建交易前评估手续费
- 监控网络拥堵状况

---

### 4. `tron_get_transaction_status`
查询交易的确认状态。

**参数:**
- `txid` (必填): 交易哈希，64 位十六进制字符串（可带 `0x` 前缀）

**返回:**
- `status`: "成功" 或 "失败" 或 "pending"
- `confirmed`: 布尔值
- `block_number`: 所在区块高度（成功/失败时）
- `confirmations`: 确认次数（如服务端提供）
- `summary`: 人类可读的摘要

**示例:**
```
查询交易 abc123...def 的状态
→ 返回: "交易 abc123... 状态：成功，所在区块 12,345,678，已确认 20 次。"
```

---

### 5. `tron_get_network_status`
获取 TRON 网络当前状态。

**参数:** 无

**返回:**
- `latest_block`: 最新区块高度
- `chain`: 链名称 (TRON Mainnet)
- `summary`: 人类可读的摘要

---

### 6. `tron_check_account_safety`
检查指定地址是否为恶意地址（钓鱼、诈骗等）。

**参数:**
- `address` (必填): TRON 地址（Base58 或 Hex 格式）

**返回:**
- `is_safe`: 地址是否安全（True/False）
- `is_risky`: 地址是否有风险标记（True/False）
- `risk_type`: 风险类型（Safe/Scam/Phishing/Unknown 等）
- `safety_status`: 安全状态描述
- `warnings`: 警告信息列表
- `summary`: 检查结果摘要

**使用场景:**
- 在转账前检查接收方地址安全性
- 验证未知地址的信誉
- 防范钓鱼和诈骗

**示例:**
```
检查地址 Txxx... 的安全性
→ 返回: "地址 Txxx... 安全状态：有风险！风险类型：Phishing（钓鱼地址）"
```

---

### 7. `tron_get_wallet_info`
查看当前配置的钱包信息。

**参数:** 无

**前置条件:** 需设置环境变量 `TRON_PRIVATE_KEY`

**返回:**
- `address`: 钱包地址
- `trx_balance`: TRX 余额
- `usdt_balance`: USDT 余额
- `summary`: 人类可读的摘要

**安全性:** 不会暴露私钥本身，仅显示从私钥派生的地址和余额

**示例:**
```
查看钱包信息
→ 返回: "钱包地址 Txxx..., TRX 余额 100.5, USDT 余额 500.0"
```

---

### 8. `tron_get_transaction_history`
查询指定地址的交易历史记录。

**参数:**
- `address` (必填): TRON 地址
- `limit` (可选): 返回交易条数，默认 10，最大 50
- `start` (可选): 偏移量（用于分页），默认 0
- `token` (可选): 代币筛选条件：
  - `None`: 查询所有类型的交易（默认）
  - `"TRX"`: 仅查询 TRX 原生转账
  - `"USDT"`: 仅查询 USDT (TRC20) 转账
  - TRC20 合约地址: 查询指定 TRC20 代币
  - TRC10 代币名称: 查询指定 TRC10 代币

**返回:**
- `address`: 查询地址
- `total`: 总交易数
- `displayed`: 当前返回的交易数
- `token_filter`: 代币筛选条件
- `transfers`: 交易列表
- `summary`: 人类可读的摘要

**示例:**
```
查询地址最近 5 笔 USDT 转账
→ 返回交易列表，包含时间、金额、对方地址等信息
```

---

### 9. `tron_build_tx`
构建未签名的转账交易。

**参数:**
- `from_address` (必填): 发送方地址
- `to_address` (必填): 接收方地址
- `amount` (必填): 转账金额（正数）
- `token` (可选): 代币类型，`USDT` 或 `TRX`，默认 `USDT`
- `force_execution` (可选): 强制执行开关，默认 `False`。当接收方存在风险时，只有设置为 `True` 才能继续构建交易。仅在用户明确说"我知道有风险，但我就是要转"时才设置为 `True`。

**返回:**
- `unsigned_tx`: 未签名交易结构，包含：
  - `txID`: 交易 ID
  - `raw_data`: 交易原始数据
- `sender_check`: 发送方余额检查结果（如果有）
- `recipient_warnings`: 接收方预警信息（如果有）
- `summary`: 人类可读的摘要

**重要安全说明:**
- 此工具会对接收方地址进行安全扫描
- 如果检测到接收方存在风险，默认会拒绝构建交易（零容忍熔断机制）
- 如需强制执行（用户明确知晓风险后坚持转账），请设置 `force_execution=True`
- 此工具仅构建交易，**不执行签名和广播**
- 交易有效期为 1 分钟

**示例:**
```
从 Txxxx 向 Tyyyy 转账 100 USDT
→ 返回: "已生成从 Txxxx... 到 Tyyyy... 转账 100 USDT 的未签名交易。"
```

---

### 10. `tron_broadcast_tx`
广播已签名的交易到 TRON 网络。

**参数:**
- `signed_tx_json` (必填): 已签名交易的 JSON 字符串

**返回:**
- `result`: 广播是否成功（True/False）
- `txid`: 交易哈希
- `summary`: 人类可读的摘要

**使用场景:**
- 配合 `tron_build_tx` 使用，构建交易后在本地签名，然后广播
- 广播从其他来源获得的已签名交易

**示例:**
```
广播已签名交易
→ 返回: "✅ 交易广播成功！交易哈希: abc123..."
```

---

### 11. `tron_transfer`
一键转账闭环：安全检查 → 构建交易 → 签名 → 广播。

**参数:**
- `to_address` (必填): 接收方地址
- `amount` (必填): 转账金额（正数）
- `token` (可选): 代币类型，`USDT` 或 `TRX`，默认 `USDT`
- `force_execution` (可选): 强制执行开关。当接收方存在风险时，只有设置为 `True` 才能继续转账。

**前置条件:** 需设置环境变量 `TRON_PRIVATE_KEY`

**返回:**
- `txid`: 交易哈希
- `result`: 转账是否成功
- `summary`: 人类可读的摘要

**安全机制:**
- **Anti-Fraud**: 检查接收方是否为恶意地址
- **Gas Guard**: 检查发送方余额是否充足
- **Recipient Check**: 检查接收方账户状态

**使用场景:**
- 需要快速完成转账的场景
- 发送方地址从本地私钥自动派生

**示例:**
```
转账 50 USDT 到 Tyyyy
→ 返回: "✅ 转账成功！交易哈希: abc123..."
```

---

## 工作流程指南

### 查询余额

```
用户: "查一下这个地址有多少 USDT: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

步骤:
1. 调用 tron_get_usdt_balance(address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
2. 返回余额信息给用户
```

### 检查交易状态

```
用户: "我的转账到账了吗？交易哈希是 abc123..."

步骤:
1. 调用 tron_get_transaction_status(txid="abc123...")
2. 如果状态是 pending，建议用户稍后再查
3. 如果状态是成功/失败，告知用户结果
```

### 安全转账（分步骤）

```
用户: "帮我转 100 USDT 到 Tyyyy"

步骤:
1. 调用 tron_check_account_safety(address="Tyyyy") 检查接收方安全性
   - 如果有风险，提醒用户并询问是否继续
2. 调用 tron_get_wallet_info() 获取本地钱包地址
3. 调用 tron_get_usdt_balance(address=钱包地址) 检查余额是否充足
4. 调用 tron_get_balance(address=钱包地址) 检查 TRX 余额是否足够支付 Gas
5. 调用 tron_build_tx(from_address=钱包地址, to_address="Tyyyy", amount=100, token="USDT") 构建交易
6. 调用 tron_broadcast_tx(signed_tx_json=签名后的交易) 广播交易
7. 调用 tron_get_transaction_status(txid=交易哈希) 确认交易结果
```

### 查看钱包概况

```
用户: "看看我的钱包"

步骤:
1. 调用 tron_get_wallet_info() 获取地址和余额
2. 调用 tron_get_transaction_history(address=钱包地址, limit=5) 获取最近交易
3. 汇总展示钱包地址、TRX/USDT 余额、最近交易
```

### 地址安全分析

```
用户: "帮我查一下这个地址安全不安全: Txxxx"

步骤:
1. 调用 tron_check_account_safety(address="Txxxx") 查看安全状态
2. 调用 tron_get_transaction_history(address="Txxxx", limit=10) 查看交易历史
3. 调用 tron_get_balance(address="Txxxx") 和 tron_get_usdt_balance(address="Txxxx") 查看资产
4. 综合分析并给出安全评估
```

### 快速转账（便捷入口）

```
用户: "快速转 50 USDT 到 Tyyyy"

步骤:
1. 调用 tron_transfer(to_address="Tyyyy", amount=50, token="USDT")
   - 内部自动完成：安全检查 → 构建 → 签名 → 广播
2. 将转账结果返回给用户
```

### 构建转账交易

```
用户: "帮我生成一个转账交易，从我的地址转 50 USDT 到 Tyyyy"

步骤:
1. 先调用 tron_get_usdt_balance 检查发送方余额是否足够
2. 调用 tron_get_gas_parameters 获取当前 Gas 价格
3. 调用 tron_build_tx(from_address="Txxxx", to_address="Tyyyy", amount=50, token="USDT")
4. 返回未签名交易，提醒用户需要签名后广播
```

---

## 错误处理

### 常见错误

| 错误类型 | 描述 | 处理建议 |
|---------|------|---------|
| `invalid_address` | 地址格式无效 | 请用户检查地址格式，应以 T 开头且 34 字符 |
| `invalid_txid` | 交易哈希格式无效 | 交易哈希应为 64 位十六进制字符 |
| `missing_param` | 缺少必填参数 | 提示用户提供所需参数 |
| `rpc_error` | 网络请求失败 | 建议用户稍后重试 |
| `timeout` | 请求超时 | 网络可能拥堵，建议稍后重试 |
| `invalid_amount` | 金额不合法 | 金额必须为正数 |
| `build_error` | 构建交易失败 | 检查参数或稍后重试 |
| `unknown_action` | 未知动作 | 核对工具名称 |
| `key_not_configured` | 私钥未配置 | 需设置环境变量 TRON_PRIVATE_KEY |
| `insufficient_balance` | 余额不足 | 检查账户余额 |

### 错误响应格式

所有错误响应包含：
- `error`: 错误类型代码
- `summary`: 人类可读的错误描述

---

## 安全注意事项

1. **私钥安全**: 私钥通过环境变量配置，不会在日志或响应中暴露
2. **地址验证**: 所有地址在使用前都会进行格式验证
3. **金额验证**: 转账金额必须为正数
4. **安全检查**: 转账前会自动检查接收方地址的安全性
5. **零容忍熔断**: 检测到风险地址时默认拒绝交易
6. **余额检查**: 构建交易前会检查发送方余额是否充足
7. **只读优先**: 查询操作不会修改链上状态

---

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **精度**: USDT 和 TRX 均使用 6 位小数
- **API**: 通过 TRONSCAN REST API 与 TRON 网络通信
- **接口来源**: account, transaction-info, chain/parameters, block
