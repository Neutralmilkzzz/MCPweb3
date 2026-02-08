---
name: tron-blockchain
description: 与 TRON 区块链交互的完整技能集。提供 14 个 MCP 标准工具，涵盖数据查询（余额、交易历史、代币持仓、内部交易、网络状态、安全检查）和交易操作（构建、签名、广播、一键转账）。支持 TRX/USDT 转账、地址安全验证、资产概览等全流程区块链操作。
---

# TRON 区块链操作技能

## 概述

此技能使你能够与 TRON 区块链进行全面交互，提供完整的链上操作能力。基于 Model Context Protocol (MCP) 标准，通过 `tron-mcp-server` 暴露 **14 个原子工具**，支持智能工作流编排。

### 架构理念
- **MCP 层**：提供原子化的工具（查询、构建、签名、广播等），每个工具职责单一
- **Skill 层**：编排多个工具形成完整工作流（如安全转账 = 安全检查 + 构建 + 签名 + 广播）
- **命名规范**：所有工具统一使用 `tron_*` 前缀，遵循 MCP 最佳实践

**核心能力**:
- 🔍 数据查询：余额、交易历史、代币持仓、内部交易、网络状态
- 🔒 安全防护：地址安全检查、钓鱼/诈骗地址识别、零容忍熔断机制
- 💸 交易操作：构建、签名、广播、一键转账（支持 TRX/USDT）
- 📊 资产管理：多代币余额、交易记录、钱包概览

**关键词**: TRON, TRX, USDT, TRC20, MCP, 余额查询, 交易历史, 内部交易, 代币持仓, 安全检查, 转账, 区块链

---

## 可用工具

此技能通过 `tron-mcp-server` MCP 服务器提供 **14 个标准工具**，分为两大类：

### 数据查询类（9 个工具）

#### 1. `tron_get_usdt_balance`
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

#### 2. `tron_get_balance`
查询指定地址的 TRX 原生代币余额。

**参数:**
- `address` (必填): TRON 地址

**返回:**
- `address`: 查询地址
- `balance_trx`: TRX 余额
- `balance_sun`: SUN 单位余额（1 TRX = 1,000,000 SUN）
- `summary`: 人类可读的摘要

---

#### 3. `tron_get_gas_parameters`
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

#### 4. `tron_get_transaction_status`
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

#### 5. `tron_get_network_status`
获取 TRON 网络当前状态。

**参数:** 无

**返回:**
- `latest_block`: 最新区块高度
- `chain`: 链名称 (TRON Mainnet)
- `summary`: 人类可读的摘要

---

#### 6. `tron_check_account_safety`
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

#### 7. `tron_get_transaction_history`
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
- `transfers`: 交易列表，每笔交易包含：
  - `timestamp`: 时间戳
  - `block`: 区块高度
  - `txID`: 交易哈希
  - `from`: 发送方地址
  - `to`: 接收方地址
  - `amount`: 转账金额
  - `token_name`: 代币名称
  - `status`: 交易状态
- `summary`: 人类可读的摘要

**使用场景:**
- 查看地址的历史转账记录
- 追踪特定代币的流动
- 分析账户活跃度

**示例:**
```
查询地址最近 5 笔 USDT 转账
→ 返回交易列表，包含时间、金额、对方地址等信息
```

---

#### 8. `tron_get_internal_transactions`
查询地址的内部交易（合约内部调用产生的转账）。

内部交易是智能合约执行过程中产生的转账，不同于普通的直接转账。
常见于 DeFi 操作（如 DEX swap）、合约间调用等场景。

**参数:**
- `address` (必填): TRON 地址
- `limit` (可选): 返回条数，默认 20，最大 50
- `start` (可选): 偏移量（分页），默认 0

**返回:**
- `address`: 查询地址
- `total`: 总内部交易数
- `displayed`: 当前返回的交易数
- `internal_transactions`: 内部交易列表，每笔交易包含：
  - `hash`: 父交易哈希
  - `block`: 区块高度
  - `timestamp`: 时间戳
  - `from`: 发送方地址
  - `to`: 接收方地址
  - `value`: 转账金额（TRX，单位 SUN）
  - `call_value`: 调用时的金额
  - `note`: 备注信息
- `summary`: 人类可读的摘要

**使用场景:**
- 追踪智能合约产生的 TRX 转账
- 分析 DeFi 操作细节
- 调试合约调用链

**示例:**
```
查询地址的内部交易记录
→ 返回合约调用产生的 TRX 转账列表
```

---

#### 9. `tron_get_account_tokens`
查询地址持有的所有代币列表（TRX + TRC20 + TRC10）。

返回完整的代币持仓信息，适用于资产概览、异常代币检测等场景。

**参数:**
- `address` (必填): TRON 地址

**返回:**
- `address`: 查询地址
- `token_count`: 持有的代币种类数量
- `tokens`: 代币列表，每个代币包含：
  - `token_id`: 代币 ID（TRC10）或合约地址（TRC20）
  - `token_name`: 代币名称
  - `token_abbr`: 代币缩写
  - `token_type`: 代币类型（TRC10/TRC20/TRX）
  - `balance`: 余额（可读格式）
  - `balance_raw`: 原始余额（最小单位）
  - `token_decimal`: 小数位数
  - `token_can_show`: 是否可显示（True/False）
- `summary`: 人类可读的摘要

**使用场景:**
- 查看钱包完整资产列表
- 检测空投的未知代币
- 资产组合分析
- 发现异常代币（可能的垃圾币/诈骗币）

**示例:**
```
查询地址持有的所有代币
→ 返回: "地址 Txxx... 持有 5 种代币：TRX (100.5), USDT (500), Token1 (1000), ..."
```

---

### 交易操作类（7 个工具）

#### 10. `tron_build_tx`
构建未签名的转账交易。

**参数:**
- `from_address` (必填): 发送方地址
- `to_address` (必填): 接收方地址
- `amount` (必填): 转账金额（正数）
- `token` (可选): 代币类型，`USDT` 或 `TRX`，默认 `USDT`
- `force_execution` (可选): 强制执行开关，默认 `False`。当接收方存在风险时，只有设置为 `True` 才能继续构建交易。仅在用户明确说"我知道有风险，但我就是要转"时才设置为 `True`。
- `memo` (可选): 交易备注/留言，默认为空字符串。会被编码为十六进制写入交易的 data 字段，在区块链浏览器上可查看。例如："还你的饭钱"、"Invoice #1234"。

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
- memo 会增加少量带宽消耗（每个字节消耗 1 带宽点）

**示例:**
```
从 Txxxx 向 Tyyyy 转账 100 USDT，备注"还你的饭钱"
→ 返回: "已生成从 Txxxx... 到 Tyyyy... 转账 100 USDT 的未签名交易。备注: 还你的饭钱"
```

---

#### 11. `tron_sign_tx`
对未签名交易进行本地签名（不广播）。

接受 `tron_build_tx` 返回的未签名交易 JSON 字符串，
使用本地私钥进行 ECDSA secp256k1 签名。

签名在本地完成，私钥永远不会通过网络传输。

**参数:**
- `unsigned_tx_json` (必填): `tron_build_tx` 返回的未签名交易 JSON 字符串

**前置条件:** 需设置环境变量 `TRON_PRIVATE_KEY`

**返回:**
- `signed_tx`: 签名后的交易对象
- `signed_tx_json`: 签名后的交易 JSON 字符串（可直接用于广播）
- `txID`: 交易哈希
- `summary`: 人类可读的摘要

**使用场景:**
- 离线签名工作流（构建 → 签名 → 广播分离）
- 冷钱包签名集成
- 多签场景

**示例:**
```
对未签名交易进行签名
→ 返回: "✅ 交易签名成功！交易 ID: abc123..."
```

---

#### 12. `tron_broadcast_tx`
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

#### 13. `tron_transfer`
一键转账闭环：安全检查 → 构建交易 → 签名 → 广播。

**参数:**
- `to_address` (必填): 接收方地址
- `amount` (必填): 转账金额（正数）
- `token` (可选): 代币类型，`USDT` 或 `TRX`，默认 `USDT`
- `force_execution` (可选): 强制执行开关。当接收方存在风险时，只有设置为 `True` 才能继续转账。
- `memo` (可选): 交易备注/留言，默认为空字符串。会被编码为十六进制写入交易的 data 字段，在区块链浏览器上可查看。例如："还你的饭钱"、"Invoice #1234"。

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
- memo 会增加少量带宽消耗（每个字节消耗 1 带宽点）

**示例:**
```
转账 50 USDT 到 Tyyyy，备注"Invoice #1234"
→ 返回: "✅ 转账成功！交易哈希: abc123..."
```

---

#### 14. `tron_get_wallet_info`
查看当前配置的钱包信息。

返回本地私钥对应的地址及其 TRX / USDT 余额。
不会暴露私钥本身。

**参数:** 无

**前置条件:** 需设置环境变量 `TRON_PRIVATE_KEY`

**返回:**
- `address`: 钱包地址
- `trx_balance`: TRX 余额
- `usdt_balance`: USDT 余额
- `summary`: 人类可读的摘要

**安全性:** 不会暴露私钥本身，仅显示从私钥派生的地址和余额

**使用场景:**
- 查看当前操作钱包的基本信息
- 确认交易前的余额状态
- 验证私钥配置是否正确

**示例:**
```
查看钱包信息
→ 返回: "钱包地址 Txxx..., TRX 余额 100.5, USDT 余额 500.0"
```

---

#### 15. `tron_lease_energy`
租赁 TRON 能量 (Energy)，用于降低 USDT 转账的 Gas 费用。

能量是执行智能合约操作（如 USDT TRC20 转账）所需的资源。通过租赁能量，可以避免在转账时燃烧 TRX 支付能量费用。

**参数:**
- `to_address` (必填): 接收能量的钱包地址（Base58 格式以 T 开头）
- `amount` (必填): 能量数量（整数，例如：65150）
- `duration` (可选): 租赁时长（小时），可选值：1 或 24，默认 1
- `activate_account` (可选): 是否同时激活账户（如果账户未激活），默认 False

**前置条件:** 需设置环境变量 `TRONZAP_API_TOKEN` 和 `TRONZAP_API_SECRET`

**返回:**
- `address`: 接收能量的地址
- `energy_amount`: 租赁的能量数量
- `duration`: 租赁时长（小时）
- `transaction_id`: 租赁交易哈希
- `cost`: 费用详情（包含 TRX 和/或 USDT）
- `status`: 交易状态（pending/success/failed）
- `summary`: 人类可读的摘要

**使用场景:**
- 账户能量不足时，租赁能量以降低 USDT 转账成本
- 批量操作前预先租赁充足能量
- 为他人租赁能量（如帮助朋友激活账户）

**示例:**
```
租赁 100000 能量到 Txxx，时长 1 小时
→ 返回: "⚡ 能量租赁请求已提交：接收地址 Txxx..., 能量数量 100,000, 租赁时长 1 小时, 交易ID: abc123..., 状态: pending"
```

---

#### 16. `tron_lease_bandwidth`
租赁 TRON 带宽 (Bandwidth)，用于降低转账的数据存储费用。

带宽是支付交易数据存储费用的资源。通过租赁带宽，可以避免在转账时消耗免费带宽或燃烧 TRX。

**参数:**
- `to_address` (必填): 接收带宽的钱包地址（Base58 格式以 T 开头）
- `amount` (必填): 带宽数量（整数，例如：1000）

**前置条件:** 需设置环境变量 `TRONZAP_API_TOKEN` 和 `TRONZAP_API_SECRET`

**返回:**
- `address`: 接收带宽的地址
- `bandwidth_amount`: 租赁的带宽数量
- `transaction_id`: 租赁交易哈希
- `cost`: 费用详情（包含 TRX 和/或 USDT）
- `status`: 交易状态（pending/success/failed）
- `summary`: 人类可读的摘要

**使用场景:**
- 账户带宽不足时，租赁带宽以降低转账成本
- 高频转账前预先租赁充足带宽
- 为他人租赁带宽

**示例:**
```
租赁 5000 带宽到 Txxx
→ 返回: "🌐 带宽租赁请求已提交：接收地址 Txxx..., 带宽数量 5,000, 交易ID: def456..., 状态: pending"
```

---

## 工作流程指南

### 查询余额（单代币）

```
用户: "查一下这个地址有多少 USDT: TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"

步骤:
1. 调用 tron_get_usdt_balance(address="TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t")
2. 返回余额信息给用户
```

### 查询全部资产

```
用户: "查一下这个地址有什么代币"

步骤:
1. 调用 tron_get_account_tokens(address="Txxx") 获取所有持有的代币
2. 对每个主要代币（TRX/USDT）调用对应的余额查询工具获取详细信息
3. 汇总展示资产列表
```

### 检查交易状态

```
用户: "我的转账到账了吗？交易哈希是 abc123..."

步骤:
1. 调用 tron_get_transaction_status(txid="abc123...")
2. 如果状态是 pending，建议用户稍后再查
3. 如果状态是成功/失败，告知用户结果
```

### 安全转账（三步走：构建 → 签名 → 广播）

```
用户: "帮我转 100 USDT 到 Tyyyy"

步骤:
1. 调用 tron_check_account_safety(address="Tyyyy") 检查接收方安全性
   - 如果有风险，提醒用户并询问是否继续
2. 调用 tron_get_wallet_info() 获取本地钱包地址
3. 调用 tron_get_usdt_balance(address=钱包地址) 检查余额是否充足
4. 调用 tron_get_balance(address=钱包地址) 检查 TRX 余额是否足够支付 Gas
5. 调用 tron_build_tx(from_address=钱包地址, to_address="Tyyyy", amount=100, token="USDT") 构建交易
   - 此步骤会自动进行安全检查，如果检测到风险会拒绝构建
6. 调用 tron_sign_tx(unsigned_tx_json=上一步返回的 unsigned_tx JSON 字符串) 对交易签名
7. 调用 tron_broadcast_tx(signed_tx_json=签名后的交易 JSON) 广播交易
8. 调用 tron_get_transaction_status(txid=交易哈希) 确认交易结果
```

### 一键转账（便捷闭环）

```
用户: "快速转 50 USDT 到 Tyyyy"

步骤:
1. 调用 tron_transfer(to_address="Tyyyy", amount=50, token="USDT")
   - 内部自动完成：安全检查 → 构建 → 签名 → 广播
2. 将转账结果返回给用户
```

### 资产概览（代币 + 历史）

```
用户: "看看我的钱包"

步骤:
1. 调用 tron_get_wallet_info() 获取地址和主要余额（TRX/USDT）
2. 调用 tron_get_account_tokens(address=钱包地址) 获取所有持有的代币
3. 调用 tron_get_transaction_history(address=钱包地址, limit=5) 获取最近交易
4. 汇总展示钱包地址、资产列表、最近交易
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

### DeFi 操作追踪

```
用户: "查一下这个地址的 DeFi 操作记录"

步骤:
1. 调用 tron_get_transaction_history(address="Txxxx", limit=20) 查看普通转账
2. 调用 tron_get_internal_transactions(address="Txxxx", limit=20) 查看内部交易
   - 内部交易通常反映智能合约调用（DEX swap、质押等）
3. 综合分析两类交易，识别 DeFi 操作模式
```

### 构建未签名交易（离线签名场景）

```
用户: "帮我生成一个转账交易，从我的地址转 50 USDT 到 Tyyyy，但先不要签名"

步骤:
1. 先调用 tron_get_usdt_balance 检查发送方余额是否足够
2. 调用 tron_get_gas_parameters 获取当前 Gas 价格
3. 调用 tron_build_tx(from_address="Txxxx", to_address="Tyyyy", amount=50, token="USDT")
4. 返回未签名交易 JSON，提醒用户需要使用 tron_sign_tx 签名后再用 tron_broadcast_tx 广播
```

---

## 高级工作流（组合工具使用）

本章节介绍如何将多个原子工具组合成智能工作流，实现自动化、优化的区块链操作。

### 1. 智能资源管理（自动租赁 + 转账）

**场景**: 用户想要转账，但账户资源（能量/带宽）不足。系统自动检测并租赁所需资源，然后执行转账。

```
用户: "转 100 USDT 到 Tyyyy，如果资源不够就自动租赁"

工作流:
1. 获取本地钱包地址（tron_get_wallet_info）
2. 查询资源状态:
   - tron_get_account_energy(address=钱包地址)
   - tron_get_account_bandwidth(address=钱包地址)
3. 判断资源是否充足:
   - USDT 转账需要约 65000 Energy
   - USDT 转账需要约 350 Bandwidth
4. 制定租赁策略:
   - 如果能量充足且带宽充足 → 直接转账
   - 如果能量不足 → 租赁能量（tron_lease_energy）
   - 如果带宽不足 → 租赁带宽（tron_lease_bandwidth）
   - 优先级：能量优先（USDT 转账能量消耗更大）
5. 执行租赁并等待确认（调用 tron_get_transaction_status）
6. 执行安全转账流程（安全检查 → 构建 → 签名 → 广播）
7. 返回完整结果，包括租赁和转账两部分信息
```

**关键点**:
- 租赁是独立交易，需要单独签名和广播
- 租赁交易确认后，资源才会到账
- 可配置租赁策略：自动选择租赁时长和数量

---

### 2. 资金流追踪（多级查询）

**场景**: 追踪一笔资金的完整流向，从源头到最终目的地。

```
用户: "追踪交易 abc123... 的资金流向"

工作流:
1. 调用 tron_get_transaction_status(txid="abc123...") 获取交易详情
   - 获取: from_address, to_address, amount, token_type
2. 根据交易方向确定追踪起点:
   - 如果用户是发送方 → 追踪资金去向 → 查询接收方地址
   - 如果用户是接收方 → 追踪资金来源 → 查询发送方地址
3. 递归追踪（可设置深度限制，如 3 层）:
   对于每个相关地址:
   - 调用 tron_get_transaction_history(address=该地址, limit=10, token=交易代币)
   - 筛选与当前资金流动相关的交易
   - 构建资金流向图谱
4. 综合分析:
   - 资金流转路径
   - 各节点地址的安全性（调用 tron_check_account_safety）
   - 时间线
5. 返回可视化或文本形式的资金流向报告
```

**示例输出**:
```
资金流向追踪（深度 3）:
第 1 层: Txxx (用户) → Tyyy (接收方), 金额 100 USDT, 时间 2026-02-09 10:30
第 2 层: Tyyy → Tzzz, 金额 80 USDT, 时间 10:35
第 3 层: Tzzz → Twww, 金额 50 USDT, 时间 10:40
...
```

---

### 3. 批量余额查询

**场景**: 同时查询多个地址的余额（如空投分发、批量审计）。

```
用户: "查一下这些地址的 USDT 余额: [Txxx, Tyyy, Tzzz]"

工作流:
1. 解析地址列表
2. 并行调用（或串行）tron_get_usdt_balance 查询每个地址
3. 汇总结果:
   - 总余额
   - 每个地址的详细余额
   - 余额排序
4. 返回表格或列表形式的结果
```

---

### 4. 自动安全审计

**场景**: 对地址进行全面的安全评估，包括黑名单检查、交易行为分析、资产分布等。

```
用户: "全面审计地址 Txxx 的安全性"

工作流:
1. 调用 tron_check_account_safety(address="Txxx") 基础安全检查
2. 调用 tron_get_transaction_history(address="Txxx", limit=20) 分析交易模式
   - 检查是否有大量小额转账（可能是洗钱）
   - 检查是否与已知风险地址交互
3. 调用 tron_get_account_tokens(address="Txxx") 查看资产分布
   - 检查是否持有大量未知代币（可能是诈骗代币）
4. 调用 tron_get_internal_transactions(address="Txxx", limit=10) 查看 DeFi 操作
   - 检查是否与恶意合约交互
5. 综合评分:
   - 黑名单标记（一票否决）
   - 交易行为异常度
   - 资产风险度
6. 返回详细审计报告
```

---

### 5. 资源优化转账（自动租赁 + 转账）

**场景**: 用户希望以最低成本完成转账，系统自动判断是否需要租赁资源，并选择最优方案。

```
用户: "用最低手续费转 100 USDT 到 Tyyyy"

工作流:
1. 获取本地钱包地址（tron_get_wallet_info）
2. 查询资源状态:
   - tron_get_account_energy(address=钱包地址)
   - tron_get_account_bandwidth(address=钱包地址)
3. 判断资源是否充足:
   - USDT 转账需要约 65000 Energy
   - USDT 转账需要约 350 Bandwidth
4. 制定优化策略:
   - 如果能量充足且带宽充足 → 直接转账
   - 如果能量不足 → 先租赁能量（tron_lease_energy）
   - 如果带宽不足 → 先租赁带宽（tron_lease_bandwidth）
   - 如果两者都不足 → 按优先级租赁（能量优先，因为 USDT 转账能量消耗更大）
5. 执行租赁（可能需要多次等待确认）
6. 执行转账（tron_transfer 或分步构建/签名/广播）
7. 返回总成本（租赁费 + 转账费）和操作结果
```

---

### 6. 交易回执与状态监控

**场景**: 用户发起交易后，持续监控直到确认。

```
用户: "转账后帮我监控直到到账"

工作流:
1. 执行转账（tron_transfer 或分步流程）
2. 获取交易哈希（txid）
3. 循环查询状态（最多 N 次，间隔 T 秒）:
   - 调用 tron_get_transaction_status(txid)
   - 如果状态为 "pending" → 继续等待
   - 如果状态为 "成功" → 返回成功，停止监控
   - 如果状态为 "失败" → 返回失败，停止监控
4. 超时处理: 如果超过最大重试次数仍未确认，建议用户手动查询
```

---

### 7. 钱包快照

**场景**: 定期记录钱包状态，用于对账或审计。

```
用户: "给我钱包做个快照"

工作流:
1. 获取钱包地址（tron_get_wallet_info）
2. 查询所有资产:
   - tron_get_balance(address)
   - tron_get_usdt_balance(address)
   - tron_get_account_tokens(address)  # 获取所有代币
3. 查询资源状态:
   - tron_get_account_energy(address)
   - tron_get_account_bandwidth(address)
4. 查询最近交易:
   - tron_get_transaction_history(address, limit=10)
5. 组装快照数据:
   - 时间戳
   - 地址
   - 资产列表（含余额）
   - 资源使用情况
   - 最近交易摘要
6. 返回结构化快照（可保存为 JSON 文件）
```

---

### 8. 地址关系分析

**场景**: 分析地址之间的关联性（如是否为同一控制人）。

```
用户: "分析地址 Txxx 和 Tyyy 是否有关联"

工作流:
1. 对每个地址:
   - 调用 tron_get_transaction_history(address, limit=50)
   - 调用 tron_get_internal_transactions(address, limit=20)
2. 提取共同点:
   - 是否有相互转账
   - 是否与相同的第三方地址频繁交互
   - 是否在同一时间段活跃
   - 是否使用相同的 memo 模式
3. 调用 tron_check_account_safety 检查两个地址的安全性
4. 综合判断:
   - 直接资金往来 → 强关联
   - 共同交易对手 → 中度关联
   - 时间重叠 → 弱关联
5. 返回关联度评分和证据
```

---

### 9. 交易深度查询与验证

**场景**: 用户提供交易哈希，需要完整验证交易的真实性和细节。

```
用户: "验证交易 abc123... 是否真实，并告诉我所有细节"

工作流:
1. 调用 tron_get_transaction_status(txid="abc123...") 获取基础状态
2. 如果交易存在且已确认:
   - 提取交易详细信息: from, to, amount, token, fee, block_number, timestamp
3. 调用 tron_check_account_safety(address=from) 检查发送方安全性
4. 调用 tron_check_account_safety(address=to) 检查接收方安全性
5. 调用 tron_get_transaction_history(address=from, limit=10) 查看发送方相关历史
6. 调用 tron_get_transaction_history(address=to, limit=10) 查看接收方相关历史
7. 综合验证:
   - 交易是否在链上确认
   - 双方地址是否安全
   - 交易金额是否合理（与历史对比）
   - 时间是否合理
8. 返回完整验证报告，包括:
   - 交易真实性
   - 双方安全状态
   - 交易上下文
   - 风险提示（如有）
```

---

### 10. 自动化转账流水账

**场景**: 记录所有转账操作，生成流水账本。

```
用户: "帮我记录最近的转账记录"

工作流:
1. 获取钱包地址（tron_get_wallet_info）
2. 调用 tron_get_transaction_history(address=钱包地址, limit=50, token="USDT") 获取 USDT 转账
3. 调用 tron_get_transaction_history(address=钱包地址, limit=50, token="TRX") 获取 TRX 转账
4. 合并并按时间排序
5. 对每笔交易:
   - 调用 tron_get_transaction_status(txid) 确认最终状态
   - 标记: 成功/失败/pending
6. 生成流水账表格:
   | 日期 | 类型 | 对方地址 | 金额 | 状态 | 交易哈希 |
   |------|------|----------|------|------|----------|
7. 计算统计:
   - 总转出金额
   - 总转入金额
   - 净流量
8. 返回流水账和统计摘要
```

---

### 11. 智能空投处理

**场景**: 用户收到空投代币，需要快速判断是否安全并决定是否领取。

```
用户: "我收到空投了，这个代币安全吗？地址是 Txxx"

工作流:
1. 调用 tron_check_account_safety(address="Txxx") 检查空投来源地址
2. 调用 tron_get_account_tokens(address="Txxx") 查看该地址持有的代币
   - 检查是否持有大量未知/可疑代币
3. 调用 tron_get_transaction_history(address="Txxx", limit=20) 分析交易模式
   - 是否频繁向多个地址发送小额代币（可能是诈骗推广）
4. 如果来源地址安全:
   - 建议用户可以领取
   - 可选：调用 tron_get_usdt_balance 查看用户当前余额
   - 提醒用户注意空投代币的价值和流动性
5. 如果来源地址有风险:
   - 明确警告用户不要交互
   - 解释风险类型（如诈骗、钓鱼等）
6. 返回安全评估和建议
```

---

### 12. 成本对比分析（租赁 vs 燃烧）

**场景**: 用户想了解是租赁资源还是直接燃烧 TRX 更划算。

```
用户: "转账 100 USDT，是租赁能量划算还是直接燃烧 TRX 划算？"

工作流:
1. 查询当前资源状态:
   - tron_get_account_energy(address=钱包地址)
   - tron_get_account_bandwidth(address=钱包地址)
2. 计算直接燃烧成本:
   - 能量费: 65000 Energy × 当前能量价格（从 tron_get_gas_parameters 获取）
   - 带宽费: 350 Bandwidth × 当前带宽价格（如有）
   - 总成本 = 能量费 + 带宽费
3. 计算租赁成本:
   - 调用 tron_lease_energy 查询租赁价格（不实际执行，仅询价）
   - 调用 tron_lease_bandwidth 查询租赁价格
   - 比较租赁费 vs 燃烧费
4. 考虑资源剩余:
   - 如果当前有充足免费资源 → 直接转账最划算
   - 如果资源不足但租赁便宜 → 建议租赁
   - 如果租赁费高于燃烧费 → 建议直接燃烧
5. 返回成本对比表格和推荐方案
```

---

## 最佳实践

### 错误处理原则

1. **每个工具调用都必须有异常捕获**
2. **网络请求失败时提供重试建议**
3. **关键操作（如转账）前必须进行安全检查**
4. **返回给用户的错误信息要友好且可操作**

### 性能优化

1. **并行查询**: 对多个独立地址的查询可以并行执行
2. **缓存**: 频繁查询的数据（如 Gas 价格）可短期缓存
3. **分页**: 查询历史记录时合理使用 limit 参数，避免一次查询过多

### 安全建议

1. **私钥保护**: 永远不要在日志或响应中暴露私钥
2. **地址验证**: 所有用户输入的地址都要经过格式验证
3. **金额限制**: 大额转账前建议用户多次确认
4. **风险提示**: 检测到风险时明确告知用户，并提供详细风险类型

---

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **精度**: USDT 和 TRX 均使用 6 位小数
- **API**: 通过 TRONSCAN REST API 与 TRON 网络通信
- **接口来源**: account, transaction-info, chain/parameters, block

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
