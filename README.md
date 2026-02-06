# TRON MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0.0-green.svg)](https://modelcontextprotocol.io/)

为 AI Agent 提供 TRON 区块链操作能力的 MCP Server，遵循 MCP 最佳实践。

[English](#english-version) | [中文](#中文版本)

---

## 中文版本

## 📖 目录

- [架构](#架构)
- [特性](#特性)
- [快速开始](#快速开始)
- [MCP 工具列表](#mcp-工具列表)
- [项目结构](#项目结构)
- [技术细节](#技术细节)
- [常见问题 FAQ](#常见问题-faq)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 架构

本项目采用 **Agent Skill + MCP Server 分离架构**：

```
┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│   tron-blockchain-skill/            │    │   tron-mcp-server/                  │
│   (Agent Skill - 知识层)             │    │   (MCP Server - 执行层)              │
│                                     │    │                                     │
│   SKILL.md                          │    │   查询工具 (Query Tools):            │
│   - 教 AI 如何使用工具               │    │   • tron_get_usdt_balance()         │
│   - 工作流程示例                     │    │   • tron_get_balance()              │
│   - 错误处理指导                     │    │   • tron_get_gas_parameters()       │
│                                     │    │   • tron_get_transaction_status()   │
└─────────────────────────────────────┘    │   • tron_get_network_status()       │
         AI 读取学习                         │   • tron_check_account_safety()     │
                                           │   • tron_get_wallet_info()          │
                                           │   • tron_get_transaction_history()  │
                                           │                                     │
                                           │   转账工具 (Transfer Tools):         │
                                           │   • tron_build_tx()                 │
                                           │   • tron_sign_tx()                  │
                                           │   • tron_broadcast_tx()             │
                                           │   • tron_transfer() ← 一键闭环      │
                                           │                                     │
                                           │   安全特性 (Security Features):      │
                                           │   🔒 Anti-Fraud (安全审计)           │
                                           │   🛡️ Gas Guard (Gas 卫士)           │
                                           │   👤 Recipient Status Check         │
                                           │   🔑 本地私钥签名 (不离开本机)        │
                                           │   ⏰ Extended Expiration (10分钟)    │
                                           └─────────────────────────────────────┘
                                                       AI 调用执行
```

## 特性

- 🔧 **标准 MCP 工具**：`tron_*` 前缀，符合 MCP 最佳实践
- 📚 **配套 Agent Skill**：独立的 SKILL.md 教 AI 如何使用
- 💰 **USDT/TRX 余额查询**：查询 TRC20 和原生代币余额
- ⛽ **Gas 参数**：获取当前网络 Gas 价格
- 📊 **交易状态**：查询交易确认状态
- 🏗️ **交易构建**：构建未签名 USDT/TRX 转账交易
- ✍️ **本地签名**：使用本地私钥进行 ECDSA secp256k1 签名，私钥不离开本机
- 📡 **交易广播**：将已签名交易广播到 TRON 网络
- 🚀 **一键转账闭环**：`tron_transfer` 自动完成 安全检查 → 构建 → 签名 → 广播 全流程
- 👛 **钱包管理**：查看本地钱包地址及余额，不暴露私钥
- 🛡️ **Gas 卫士 (Anti-Revert)**：在构建交易前强制检查发送方余额，预估 Gas 费用，拦截"必死交易"
- 👤 **接收方状态检测**：自动识别接收方地址是否为未激活状态，提示额外能量消耗
- ⏰ **交易有效期延长**：交易过期时间延长至 10 分钟，为人工签名提供充足时间窗口
- 🔒 **安全审计 (Anti-Fraud)**：集成 TRONSCAN 官方黑名单 API，在构建交易前识别恶意地址（诈骗、钓鱼等），保护用户资产安全
- 📜 **交易历史查询**：支持查询指定地址的 TRX/TRC20 交易历史记录，支持按代币类型筛选和分页

## 快速开始

### 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / macOS / Linux

### 1. 安装依赖

**Windows:**
```powershell
cd tron-mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd tron-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，按需配置：
# - TRON_PRIVATE_KEY: 签名/广播交易时必需
# - TRONSCAN_API_KEY: 提高 API 限额（推荐）
# - Gas 估算参数: 可根据网络状况微调
```

### 3. 运行 MCP Server

**方式一：stdio 模式（默认，用于 Claude Desktop 等）**

```bash
python -m tron_mcp_server.server
```

**方式二：SSE 模式（HTTP 端口，用于 Cursor 等）**

```bash
python -m tron_mcp_server.server --sse
```

默认监听 `http://127.0.0.1:8765/sse`，可通过环境变量 `MCP_PORT` 修改端口。

> ⚠️ **端口占用**：如果 8765 端口被占用，可设置 `MCP_PORT=8766` 或其他可用端口。

### 4. 客户端配置

**Cursor (SSE 模式)**

1. 打开 Cursor Settings -> Features -> MCP Servers
2. 点击 + Add New MCP Server
3. 配置如下：
   - **Name**: `tron`
   - **Type**: `sse`
   - **URL**: `http://127.0.0.1:8765/sse`

**Cursor (Stdio 模式，自动管理进程)**

1. 同上打开 MCP Servers 设置
2. 配置如下：
   - **Name**: `tron`
   - **Type**: `command`
   - **Command**: 
     - Windows: `cmd /c "cd /d C:\path\to\tron-mcp-server && ..\.venv\Scripts\python.exe -m tron_mcp_server.server"`
     - macOS/Linux: `cd /path/to/tron-mcp-server && ../.venv/bin/python -m tron_mcp_server.server`

**Claude Desktop (stdio 模式)**

编辑 `claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "tron": {
      "command": "python",
      "args": ["-m", "tron_mcp_server.server"],
      "cwd": "/path/to/tron-mcp-server"
    }
  }
}
```

## MCP 工具列表

### 查询工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `tron_get_usdt_balance` | 查询 USDT 余额 | `address` |
| `tron_get_balance` | 查询 TRX 余额 | `address` |
| `tron_get_gas_parameters` | 获取 Gas 参数 | 无 |
| `tron_get_transaction_status` | 查询交易确认状态 | `txid` |
| `tron_get_network_status` | 获取网络状态 | 无 |
| `tron_check_account_safety` | 检查地址安全性（TRONSCAN 黑名单 + 多维风控） | `address` |
| `tron_get_wallet_info` | 查看本地钱包地址、TRX/USDT 余额（不暴露私钥） | 无 |
| `tron_get_transaction_history` | 查询地址的交易历史记录（支持按代币类型筛选） | `address`, `limit`, `start`, `token` |

### 转账工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `tron_build_tx` | 构建未签名交易（含安全审计 + Gas 拦截） | `from_address`, `to_address`, `amount`, `token`, `force_execution` |
| `tron_sign_tx` | 构建并签名交易，不广播（需 `TRON_PRIVATE_KEY`） | `from_address`, `to_address`, `amount`, `token` |
| `tron_broadcast_tx` | 广播已签名交易到 TRON 网络 | `signed_tx_json` |
| `tron_transfer` | 🚀 一键转账闭环：安全检查 → 构建 → 签名 → 广播 | `to_address`, `amount`, `token`, `force_execution` |

## 项目结构

```
.
├── tron-blockchain-skill/           # Agent Skill（知识层）
│   ├── SKILL.md                     # AI 读取的技能说明
│   └── LICENSE.txt
├── tron-mcp-server/                 # MCP Server（执行层）
│   ├── tron_mcp_server/             # Python 包
│   │   ├── __init__.py              # 包入口
│   │   ├── server.py                # MCP Server 入口（暴露 tron_* 工具）
│   │   ├── call_router.py           # 调用路由器
│   │   ├── skills.py                # 技能清单定义
│   │   ├── tron_client.py           # TRONSCAN REST 客户端（查询）
│   │   ├── trongrid_client.py       # TronGrid API 客户端（交易构建/广播）
│   │   ├── tx_builder.py            # 交易构建器（含安全检查）
│   │   ├── key_manager.py           # 本地私钥管理（签名/地址派生）
│   │   ├── validators.py            # 参数校验
│   │   ├── formatters.py            # 输出格式化
│   │   └── config.py                # 配置管理
│   ├── test_known_issues.py         # 已知问题测试
│   ├── test_transfer_flow.py        # 转账流程测试
│   ├── test_tx_builder_new.py       # 交易构建测试
│   ├── test_transaction_history.py  # 交易历史查询测试
│   ├── requirements.txt             # 依赖
│   └── .env.example                 # 环境变量示例
├── Changelog.md                     # 更新日志
└── README.md                        # 本文件
```

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **查询 API**: TRONSCAN REST（余额、交易状态、Gas 参数、安全检查）
- **交易 API**: TronGrid（构建真实交易、广播签名交易）
- **签名算法**: ECDSA secp256k1 + RFC 6979 确定性签名
- **地址派生**: 私钥 → secp256k1 公钥 → Keccak256 → Base58Check
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）
- **关键依赖**: `mcp`, `httpx`, `ecdsa`, `pycryptodome`, `base58`

## 🔒 安全审计 (Anti-Fraud)

本服务集成了 TRONSCAN 官方安全 API，在构建交易前自动检测接收方地址的风险状态，保护用户资产安全。

### 检测来源

| API | 端点 | 用途 |
|-----|------|------|
| Account Detail API | `/api/accountv2` | 获取地址标签（redTag, greyTag, blueTag, publicTag）和用户投诉状态 |
| Security Service API | `/api/security/account/data` | 获取黑名单状态、欺诈交易记录、假币创建者等行为指标 |

### 风险指标

| 指标 | 风险等级 | 说明 |
|------|----------|------|
| 🔴 redTag | 高危 | TRONSCAN 官方标记的诈骗/钓鱼地址 |
| ⚪ greyTag | 存疑 | 存在争议或可疑行为的地址 |
| ⚠️ feedbackRisk | 用户投诉 | 存在多起用户举报 |
| 💀 is_black_list | 黑名单 | 被 USDT/稳定币发行方列入黑名单 |
| 💸 has_fraud_transaction | 欺诈历史 | 曾有欺诈交易记录 |
| 🪙 fraud_token_creator | 假币创建者 | 创建过假冒代币 |
| 📢 send_ad_by_memo | 垃圾账号 | 通过 memo 发送广告的垃圾账号 |

### 使用建议

1. **构建交易前**：`tron_build_tx` 工具会自动调用安全检查，若检测到风险会返回警告
2. **手动查询**：可通过 `check_account_risk(address)` 函数主动查询任意地址的风险状态
3. **API Key 配置**：建议在 `.env` 文件中配置 `TRONSCAN_API_KEY` 以获得更高的 API 调用限额，避免因限流（Rate Limit）导致问题

---

## ⚠️ 已知问题与改善计划 (Known Issues & Roadmap)

> 以下是经过系统审计后识别的已知问题，按严重程度排序。所有问题均已有测试覆盖（见 `test_known_issues.py`）。

### ✅ 已修复：地址校验漏洞 + TRX 余额查询异常 (v1.0.2)

| 项目 | 说明 |
|------|------|
| **validators.py** | 非 34 字符的 T 开头地址不再通过宽松校验，直接返回 False |
| **tron_client.py** | `get_balance_trx()` 查询新地址不再抛异常，正确返回 0 |

### 🔴 严重：API 失败时的静默失效 (Silent Failure)

| 项目 | 说明 |
|------|------|
| **位置** | `tron_client.py` → `check_account_risk()` |
| **问题** | 当两个安全 API（accountv2 + security）**同时失败**（如 429 频率限制、网络断开），代码通过 `except Exception` 默认返回 `is_risky=False, risk_type="Safe"` |
| **风险** | 金融安全工具中"静默失效"是最危险的缺陷。评委测试时如果 API 恰好超频，所有地址都会显示"安全" |
| **改善方向** | 1. 双 API 失败时 `risk_type` 设为 `"Unknown"`<br>2. 添加降级提示 `"⚠️ 安全检查服务暂时不可用，请谨慎操作"`<br>3. `check_recipient_security()` 中 API 失败时考虑不默认放行 |

### 🟡 中等：手续费估算未接入免费带宽抵扣 (Free Bandwidth Gap)

| 项目 | 说明 |
|------|------|
| **位置** | `tx_builder.py` → `check_sender_balance()` |
| **问题** | USDT 手续费固定按 `65000 Energy × 420 SUN = 27.3 TRX` 估算，未接入 TRON 每地址每天 600 免费带宽的动态抵扣 |
| **影响** | USDT 转账消耗 ~350 bytes 带宽，免费带宽可节省 ~0.35 TRX。余额在 26.95~27.30 TRX 之间的用户可能被误报"余额不足" |
| **改善方向** | 查询用户剩余免费带宽，动态调整 Gas 估算 |

### 🟡 中等：`force_execution` 的 LLM 提示词风险

| 项目 | 说明 |
|------|------|
| **位置** | `tx_builder.py` → `build_unsigned_tx()`, `SKILL.md` |
| **问题** | 拦截交易时返回字符串提示 LLM "用户说强制才可以"，但如果提示词不够清晰，LLM 可能陷入"对不起我不能转"的死循环，或错误地自行决定强制执行 |
| **改善方向** | 在 SKILL.md 中加强提示：只有用户**明确说**"我知道有风险，但我就是要转"才设置 `force_execution=True` |

### 🟢 低等：交易确认工作流待优化

| 项目 | 说明 |
|------|------|
| **位置** | `tron_client.py` → `get_transaction_status()` |
| **现状** | 功能已实现，可通过 `transaction-info?hash={hash}` 查询链上确认状态 |
| **待优化** | 在 SKILL.md 中增加"转账后查询确认"推荐工作流，让 AI 主动引导用户使用 `tron_get_transaction_status` 查询到账情况 |

### 测试覆盖

所有上述问题均在 `test_known_issues.py` 中有对应测试用例：

```bash
cd tron-mcp-server
python -m pytest test_known_issues.py -v
```

---

## 常见问题 FAQ

### Q1: 如何切换到测试网？
A: 修改 `.env` 文件中的 `TRONSCAN_API_URL` 为测试网 API 地址（如 Shasta 测试网）。

### Q2: 端口 8765 被占用怎么办？
A: 设置环境变量 `MCP_PORT=8766`（或其他可用端口）后重新启动服务。

### Q3: MCP Server 无法连接到 AI 客户端？
A: 
1. 确认服务已正常启动
2. 检查配置文件中的路径是否正确
3. 查看 AI 客户端日志获取详细错误信息
4. 确保使用了正确的运行模式（stdio 或 SSE）

### Q4: 如何调试 MCP Server？
A: 可以直接运行 `python -m tron_mcp_server.server` 查看控制台输出，或在代码中添加日志语句。

### Q5: 支持哪些代币？
A: 目前支持 TRX（原生代币）和 USDT（TRC20）。未来可扩展支持更多 TRC20 代币。

### Q6: 交易构建后如何签名和广播？
A: 有两种方式：
1. **使用内置工具（推荐）**：设置环境变量 `TRON_PRIVATE_KEY`，然后使用 `tron_sign_tx` 签名 + `tron_broadcast_tx` 广播，或直接用 `tron_transfer` 一键完成全流程。
2. **使用外部工具**：`tron_build_tx` 生成未签名交易后，使用 TronLink、硬件钱包等私钥管理工具在本地签名，然后通过 TRON 节点广播。

### Q8: 如何配置本地私钥用于签名？
A: 设置环境变量 `TRON_PRIVATE_KEY` 为 64 位十六进制字符串（不含 0x 前缀）。私钥仅在本地使用，不会通过 MCP 工具暴露给 AI Agent。

### Q9: `tron_transfer` 一键转账安全吗？
A: `tron_transfer` 在广播前会自动执行全部安全检查（Anti-Fraud 安全审计 + Gas Guard 余额拦截 + 接收方状态检测）。私钥始终在本地完成签名，不离开本机。

### Q7: API 速率限制怎么办？
A: 可以在 `.env` 中配置 `TRONSCAN_API_KEY` 以提高速率限制，或实现请求缓存。

---

## 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 开发规范

- 遵循 PEP 8 Python 代码规范
- 为新功能添加测试用例
- 更新相关文档
- 确保所有测试通过

### 报告问题

如果发现 bug 或有功能建议，请在 [Issues](https://github.com/Neutralmilkzzz/MCPweb3/issues) 中提出。

---

## 致谢

感谢 [Anthropic](https://www.anthropic.com/) 开发的 MCP 协议，以及 TRON 生态系统的支持。

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<a name="english-version"></a>

## English Version

# TRON MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-1.0.0-green.svg)](https://modelcontextprotocol.io/)

A Model Context Protocol (MCP) Server that provides AI Agents with TRON blockchain operation capabilities, following MCP best practices.

## 📖 Table of Contents

- [Architecture](#architecture-en)
- [Features](#features-en)
- [Quick Start](#quick-start-en)
- [MCP Tools](#mcp-tools-en)
- [Project Structure](#project-structure-en)
- [Technical Details](#technical-details-en)
- [FAQ](#faq-en)
- [Contributing](#contributing-en)
- [License](#license-en)

<a name="architecture-en"></a>

## Architecture

This project uses an **Agent Skill + MCP Server separation architecture**:

```
┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│   tron-blockchain-skill/            │    │   tron-mcp-server/                  │
│   (Agent Skill - Knowledge)         │    │   (MCP Server - Execution)          │
│                                     │    │                                     │
│   SKILL.md                          │    │   Query Tools:                      │
│   - Teach AI how to use tools       │    │   • tron_get_usdt_balance()         │
│   - Workflow examples               │    │   • tron_get_balance()              │
│   - Error handling guidance         │    │   • tron_get_gas_parameters()       │
│                                     │    │   • tron_get_transaction_status()   │
└─────────────────────────────────────┘    │   • tron_get_network_status()       │
         AI reads and learns                │   • tron_check_account_safety()     │
                                           │   • tron_get_wallet_info()          │
                                           │   • tron_get_transaction_history()  │
                                           │                                     │
                                           │   Transfer Tools:                   │
                                           │   • tron_build_tx()                 │
                                           │   • tron_sign_tx()                  │
                                           │   • tron_broadcast_tx()             │
                                           │   • tron_transfer() ← Full Flow     │
                                           │                                     │
                                           │   Security Features:                │
                                           │   🔒 Anti-Fraud (Security Audit)    │
                                           │   🛡️ Gas Guard (Anti-Revert)        │
                                           │   👤 Recipient Status Check         │
                                           │   🔑 Local Key Signing              │
                                           │   ⏰ Extended Expiration (10min)    │
                                           └─────────────────────────────────────┘
                                                       AI calls and executes
```

<a name="features-en"></a>

## Features

- 🔧 **Standard MCP Tools**: `tron_*` prefix, following MCP best practices
- 📚 **Agent Skill Support**: Separate SKILL.md teaches AI how to use the tools
- 💰 **USDT/TRX Balance Query**: Query TRC20 and native token balances
- ⛽ **Gas Parameters**: Get current network gas prices
- 📊 **Transaction Status**: Query transaction confirmation status
- 🏗️ **Transaction Building**: Build unsigned USDT/TRX transfer transactions
- ✍️ **Local Signing**: ECDSA secp256k1 signing with local private key — key never leaves the machine
- 📡 **Transaction Broadcasting**: Broadcast signed transactions to TRON network
- 🚀 **One-Click Transfer**: `tron_transfer` auto-completes full flow: safety check → build → sign → broadcast
- 👛 **Wallet Management**: View local wallet address and balances without exposing private key
- 🛡️ **Gas Guard (Anti-Revert)**: Pre-validates sender balance and estimated gas before building transactions to prevent doomed transactions
- 👤 **Recipient Status Check**: Automatically detects if recipient address is unactivated, warns about extra energy costs
- ⏰ **Extended Expiration**: Transaction expiration extended to 10 minutes, providing sufficient time for manual signing
- 🔒 **Security Audit (Anti-Fraud)**: Integrates TRONSCAN official blacklist API to identify malicious addresses (Scam, Phishing, etc.) before transaction construction, protecting user assets
- 📜 **Transaction History**: Query TRX/TRC20 transaction history for any address, with token type filtering and pagination support

<a name="quick-start-en"></a>

## Quick Start

### Requirements

- **Python**: 3.10 or higher
- **Operating System**: Windows / macOS / Linux

### 1. Install Dependencies

**Windows:**
```powershell
cd tron-mcp-server
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd tron-mcp-server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env file to configure as needed:
# - TRON_PRIVATE_KEY: Required for signing/broadcasting transactions
# - TRONSCAN_API_KEY: Increase API rate limits (recommended)
# - Gas estimation parameters: Fine-tune based on network conditions
```

### 3. Run MCP Server

**Method 1: stdio mode (default, for Claude Desktop, etc.)**

```bash
python -m tron_mcp_server.server
```

**Method 2: SSE mode (HTTP port, for Cursor, etc.)**

```bash
python -m tron_mcp_server.server --sse
```

Default listening on `http://127.0.0.1:8765/sse`, port can be modified via `MCP_PORT` environment variable.

> ⚠️ **Port Conflict**: If port 8765 is occupied, set `MCP_PORT=8766` or another available port.

### 4. Client Configuration

**Cursor (SSE mode)**

1. Open Cursor Settings -> Features -> MCP Servers
2. Click + Add New MCP Server
3. Configure as follows:
   - **Name**: `tron`
   - **Type**: `sse`
   - **URL**: `http://127.0.0.1:8765/sse`

**Cursor (Stdio mode, auto-managed process)**

1. Open MCP Servers settings as above
2. Configure as follows:
   - **Name**: `tron`
   - **Type**: `command`
   - **Command**: 
     - Windows: `cmd /c "cd /d C:\path\to\tron-mcp-server && ..\.venv\Scripts\python.exe -m tron_mcp_server.server"`
     - macOS/Linux: `cd /path/to/tron-mcp-server && ../.venv/bin/python -m tron_mcp_server.server`

**Claude Desktop (stdio mode)**

Edit `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tron": {
      "command": "python",
      "args": ["-m", "tron_mcp_server.server"],
      "cwd": "/path/to/tron-mcp-server"
    }
  }
}
```

<a name="mcp-tools-en"></a>

## MCP Tools

### Query Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `tron_get_usdt_balance` | Query USDT balance | `address` |
| `tron_get_balance` | Query TRX balance | `address` |
| `tron_get_gas_parameters` | Get Gas parameters | None |
| `tron_get_transaction_status` | Query transaction confirmation status | `txid` |
| `tron_get_network_status` | Get network status | None |
| `tron_check_account_safety` | Check address safety (TRONSCAN blacklist + multi-dim risk scan) | `address` |
| `tron_get_wallet_info` | View local wallet address & TRX/USDT balances (no key exposure) | None |
| `tron_get_transaction_history` | Query transaction history for an address (supports token type filtering) | `address`, `limit`, `start`, `token` |

### Transfer Tools

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `tron_build_tx` | Build unsigned transaction (with security audit + gas guard) | `from_address`, `to_address`, `amount`, `token`, `force_execution` |
| `tron_sign_tx` | Build & sign transaction without broadcasting (requires `TRON_PRIVATE_KEY`) | `from_address`, `to_address`, `amount`, `token` |
| `tron_broadcast_tx` | Broadcast signed transaction to TRON network | `signed_tx_json` |
| `tron_transfer` | 🚀 One-click transfer: safety check → build → sign → broadcast | `to_address`, `amount`, `token`, `force_execution` |

<a name="project-structure-en"></a>

## Project Structure

```
.
├── tron-blockchain-skill/           # Agent Skill (Knowledge layer)
│   ├── SKILL.md                     # Skill documentation for AI
│   └── LICENSE.txt
├── tron-mcp-server/                 # MCP Server (Execution layer)
│   ├── tron_mcp_server/             # Python package
│   │   ├── __init__.py              # Package entry
│   │   ├── server.py                # MCP Server entry (exposes tron_* tools)
│   │   ├── call_router.py           # Call router
│   │   ├── skills.py                # Skill manifest definitions
│   │   ├── tron_client.py           # TRONSCAN REST client (queries)
│   │   ├── trongrid_client.py       # TronGrid API client (tx build/broadcast)
│   │   ├── tx_builder.py            # Transaction builder (with safety checks)
│   │   ├── key_manager.py           # Local private key management (sign/derive)
│   │   ├── validators.py            # Parameter validation
│   │   ├── formatters.py            # Output formatting
│   │   └── config.py                # Configuration management
│   ├── test_known_issues.py         # Known issues tests
│   ├── test_transfer_flow.py        # Transfer flow tests
│   ├── test_tx_builder_new.py       # Transaction builder tests
│   ├── test_transaction_history.py  # Transaction history tests
│   ├── requirements.txt             # Dependencies
│   └── .env.example                 # Environment variables example
├── Changelog.md                     # Update log
└── README.md                        # This file
```

<a name="technical-details-en"></a>

## Technical Details

- **USDT Contract**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 decimals)
- **Query API**: TRONSCAN REST (balances, tx status, gas params, security checks)
- **Transaction API**: TronGrid (build real transactions, broadcast signed transactions)
- **Signing Algorithm**: ECDSA secp256k1 + RFC 6979 deterministic signing
- **Address Derivation**: Private key → secp256k1 pubkey → Keccak256 → Base58Check
- **Transport Protocol**: stdio (default) / SSE (`--sse` startup)
- **Default Port**: 8765 (SSE mode, configurable via `MCP_PORT` environment variable)
- **Key Dependencies**: `mcp`, `httpx`, `ecdsa`, `pycryptodome`, `base58`

## 🔒 Security Audit (Anti-Fraud)

This service integrates TRONSCAN official security APIs to automatically detect risk status of recipient addresses before building transactions, protecting user assets.

### Detection Sources

| API | Endpoint | Purpose |
|-----|----------|---------|
| Account Detail API | `/api/accountv2` | Get address tags (redTag, greyTag, blueTag, publicTag) and user complaint status |
| Security Service API | `/api/security/account/data` | Get blacklist status, fraud transaction history, fake token creator, etc. |

### Risk Indicators

| Indicator | Risk Level | Description |
|-----------|------------|-------------|
| 🔴 redTag | High Risk | TRONSCAN officially flagged scam/phishing address |
| ⚪ greyTag | Suspicious | Address with disputed or suspicious behavior |
| ⚠️ feedbackRisk | User Reported | Multiple user complaints exist |
| 💀 is_black_list | Blacklisted | Blacklisted by USDT/stablecoin issuers |
| 💸 has_fraud_transaction | Fraud History | Has fraud transaction history |
| 🪙 fraud_token_creator | Fake Token Creator | Has created fraudulent tokens |
| 📢 send_ad_by_memo | Spam Account | Spam account that sends advertisements via memo |

### Usage Recommendations

1. **Before Building Transactions**: The `tron_build_tx` tool automatically calls security checks and returns warnings if risks are detected
2. **Manual Query**: Use `check_account_risk(address)` function to actively query risk status of any address
3. **API Key Configuration**: It's recommended to configure `TRONSCAN_API_KEY` in `.env` file to get higher API call limits and avoid rate limiting issues

---

## ⚠️ Known Issues & Roadmap

> The following are known issues identified through systematic auditing, sorted by severity. All issues have test coverage (see `test_known_issues.py`).

### ✅ Fixed: Address Validation Vulnerability + TRX Balance Query Exception (v1.0.2)

| Item | Description |
|------|-------------|
| **validators.py** | T-prefixed addresses with non-34 characters no longer pass lenient validation, directly return False |
| **tron_client.py** | `get_balance_trx()` querying new addresses no longer throws exception, correctly returns 0 |

### 🔴 Critical: Silent Failure on API Errors

| Item | Description |
|------|-------------|
| **Location** | `tron_client.py` → `check_account_risk()` |
| **Issue** | When both security APIs (accountv2 + security) **fail simultaneously** (e.g., 429 rate limit, network disconnection), code defaults to `is_risky=False, risk_type="Safe"` via `except Exception` |
| **Risk** | "Silent failure" is the most dangerous defect in financial security tools. If APIs happen to exceed rate limits during testing, all addresses would show as "safe" |
| **Improvement Direction** | 1. Set `risk_type` to `"Unknown"` when both APIs fail<br>2. Add fallback warning `"⚠️ Security check service temporarily unavailable, please proceed with caution"`<br>3. Consider not defaulting to allow pass in `check_recipient_security()` when API fails |

### 🟡 Medium: Fee Estimation Missing Free Bandwidth Deduction

| Item | Description |
|------|-------------|
| **Location** | `tx_builder.py` → `check_sender_balance()` |
| **Issue** | USDT fees are fixed at `65000 Energy × 420 SUN = 27.3 TRX` estimation, without integrating TRON's daily 600 free bandwidth per address for dynamic deduction |
| **Impact** | USDT transfers consume ~350 bytes bandwidth, free bandwidth can save ~0.35 TRX. Users with balance between 26.95~27.30 TRX may be falsely reported as "insufficient balance" |
| **Improvement Direction** | Query user's remaining free bandwidth, dynamically adjust Gas estimation |

### 🟡 Medium: `force_execution` LLM Prompt Risk

| Item | Description |
|------|-------------|
| **Location** | `tx_builder.py` → `build_unsigned_tx()`, `SKILL.md` |
| **Issue** | When intercepting transactions, returns string prompting LLM "only if user says force", but if prompt is not clear enough, LLM may fall into "sorry I can't transfer" infinite loop, or incorrectly decide to force execution on its own |
| **Improvement Direction** | Strengthen prompt in SKILL.md: only set `force_execution=True` when user **explicitly says** "I know there are risks, but I want to transfer anyway" |

### 🟢 Low: Transaction Confirmation Workflow Pending Optimization

| Item | Description |
|------|-------------|
| **Location** | `tron_client.py` → `get_transaction_status()` |
| **Current Status** | Feature implemented, can query on-chain confirmation status via `transaction-info?hash={hash}` |
| **Pending Optimization** | Add "post-transfer query confirmation" recommended workflow in SKILL.md, let AI proactively guide users to use `tron_get_transaction_status` to check arrival status |

### Test Coverage

All above issues have corresponding test cases in `test_known_issues.py`:

```bash
cd tron-mcp-server
python -m pytest test_known_issues.py -v
```

---

<a name="faq-en"></a>

## FAQ

### Q1: How to switch to testnet?
A: Modify `TRONSCAN_API_URL` in `.env` file to testnet API address (e.g., Shasta testnet).

### Q2: Port 8765 is occupied?
A: Set environment variable `MCP_PORT=8766` (or another available port) and restart the service.

### Q3: MCP Server cannot connect to AI client?
A: 
1. Confirm the service has started properly
2. Check if paths in configuration files are correct
3. View AI client logs for detailed error information
4. Ensure the correct running mode (stdio or SSE) is used

### Q4: How to debug MCP Server?
A: Run `python -m tron_mcp_server.server` directly to see console output, or add logging statements in the code.

### Q5: Which tokens are supported?
A: Currently supports TRX (native token) and USDT (TRC20). More TRC20 tokens can be supported in the future.

### Q6: How to sign and broadcast after building a transaction?
A: Two options:
1. **Built-in tools (recommended)**: Set env var `TRON_PRIVATE_KEY`, then use `tron_sign_tx` + `tron_broadcast_tx`, or simply use `tron_transfer` for one-click full flow.
2. **External tools**: After `tron_build_tx` generates unsigned transaction, sign with TronLink, hardware wallet, etc., then broadcast via TRON nodes.

### Q8: How to configure local private key for signing?
A: Set env var `TRON_PRIVATE_KEY` to a 64-char hex string (without 0x prefix). The key is only used locally and never exposed to AI Agent via MCP tools.

### Q9: Is `tron_transfer` one-click transfer secure?
A: `tron_transfer` runs all security checks (Anti-Fraud + Gas Guard + Recipient Status) before broadcasting. The private key always remains local — signing happens on your machine only.

### Q7: What about API rate limits?
A: Configure `TRONSCAN_API_KEY` in `.env` to increase rate limits, or implement request caching.

<a name="contributing-en"></a>

## Contributing

We welcome all forms of contributions!

### How to Contribute

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 Python coding standards
- Add test cases for new features
- Update relevant documentation
- Ensure all tests pass

### Reporting Issues

If you find a bug or have a feature suggestion, please submit it in [Issues](https://github.com/Neutralmilkzzz/MCPweb3/issues).

---

## Acknowledgments

Thanks to [Anthropic](https://www.anthropic.com/) for developing the MCP protocol, and the TRON ecosystem for their support.

---

<a name="license-en"></a>

## License

MIT License - See [LICENSE](LICENSE) file for details
