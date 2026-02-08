# TRON MCP Server

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

为 AI Agent 提供 TRON 区块链操作能力的 MCP Server，遵循 MCP 最佳实践。

> 📖 完整文档请查看根目录的 [README.md](../README.md)

## 架构

本项目采用 **Agent Skill + MCP Server 分离架构**：

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   tron-blockchain-skill/        │    │   tron-mcp-server/              │
│   (Agent Skill - 知识层)         │    │   (MCP Server - 执行层)          │
│                                 │    │                                 │
│   SKILL.md                      │    │   查询: tron_get_*()              │
│   - 教 AI 如何使用工具           │    │   转账: tron_build/sign/broadcast │
│   - 工作流程示例                 │    │   闭环: tron_transfer()           │
│   - 错误处理指导                 │    │   钱包: tron_get_wallet_info()    │
│                                 │    │   安全: tron_check_account_safety │
└─────────────────────────────────┘    └─────────────────────────────────┘
         AI 读取学习                              AI 调用执行
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
- 🚀 **一键转账闭环**：`tron_transfer` 自动完成安全检查 → 构建 → 签名 → 广播
- 👛 **钱包管理**：查看本地钱包地址及余额，不暴露私钥
- 🛡️ **Gas 卫士**：拦截余额不足的"必死交易"
- 🔒 **安全审计**：集成 TRONSCAN 黑名单 API 识别恶意地址

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
# 编辑 .env 文件，按需配置 TRONSCAN API
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
| `tron_get_transaction_status` | 查询交易状态 | `txid` |
| `tron_get_network_status` | 获取网络状态 | 无 |
| `tron_check_account_safety` | 检查地址安全性（TRONSCAN 黑名单 + 多维风控） | `address` |
| `tron_get_wallet_info` | 查看本地钱包地址和余额（不暴露私钥） | 无 |
| `tron_get_account_energy` | 查询账户能量(Energy)资源情况 | `address` |
| `tron_get_account_bandwidth` | 查询账户带宽(Bandwidth)资源情况 | `address` |

### 转账工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `tron_build_tx` | 构建未签名交易（含安全审计 + Gas 拦截） | `from_address`, `to_address`, `amount`, `token`, `force_execution`, `memo` |
| `tron_sign_tx` | 构建并签名交易，不广播（需 `TRON_PRIVATE_KEY`） | `from_address`, `to_address`, `amount`, `token` |
| `tron_broadcast_tx` | 广播已签名交易到 TRON 网络 | `signed_tx_json` |
| `tron_transfer` | 🚀 一键转账闭环：安全检查 → 构建 → 签名 → 广播 | `to_address`, `amount`, `token`, `force_execution`, `memo` |

## 配套 Agent Skill

AI 通过加载 `tron-blockchain-skill/SKILL.md` 来学习如何使用这些工具：

```
../tron-blockchain-skill/
├── SKILL.md       # AI 读取的技能说明
└── LICENSE.txt
```

Skill 文件包含：
- 每个工具的详细参数说明
- 返回值格式
- 工作流程示例
- 错误处理指导

## 项目结构

```
tron-mcp-server/
├── tron_mcp_server/
│   ├── __init__.py           # 包入口
│   ├── server.py             # MCP Server（暴露 tron_* 工具）
│   ├── call_router.py        # 调用路由器
│   ├── skills.py             # 技能清单定义
│   ├── tron_client.py        # TRONSCAN REST 客户端（查询）
│   ├── trongrid_client.py    # TronGrid API 客户端（交易构建/广播）
│   ├── tx_builder.py         # 交易构建器（含安全检查）
│   ├── key_manager.py        # 本地私钥管理（签名/地址派生）
│   ├── validators.py         # 参数校验
│   ├── formatters.py         # 输出格式化
│   └── config.py             # 配置管理
├── test_known_issues.py      # 已知问题测试
├── test_transfer_flow.py     # 转账流程测试
├── test_tx_builder_new.py    # 交易构建测试
├── requirements.txt          # 依赖
└── .env.example              # 环境变量示例
```

## 开发

### 运行测试

```bash
python -m pytest test_known_issues.py test_transfer_flow.py test_tx_builder_new.py -v
```

### 测试覆盖

- ✅ 技能 Schema 验证
- ✅ 路由器功能测试
- ✅ TRONSCAN 客户端解析
- ✅ 交易构建
- ✅ 参数校验
- ✅ 格式化输出
- ✅ 错误处理
- ✅ 转账流程（签名 / 广播 / 一键转账）
- ✅ 私钥管理与地址派生
- ✅ 安全审计与风控拦截

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **查询 API**: TRONSCAN REST（余额、交易状态、Gas 参数、安全检查）
- **交易 API**: TronGrid（构建真实交易、广播签名交易）
- **签名算法**: ECDSA secp256k1 + RFC 6979 确定性签名
- **地址派生**: 私钥 → secp256k1 公钥 → Keccak256 → Base58Check
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）
- **关键依赖**: `mcp`, `httpx`, `ecdsa`, `pycryptodome`, `base58`

## 常见问题

参见根目录 [README.md](../README.md#常见问题-faq) 中的完整 FAQ 部分。

## 贡献

欢迎贡献！请查看根目录的 [贡献指南](../README.md#贡献指南)。

## 许可证

MIT
