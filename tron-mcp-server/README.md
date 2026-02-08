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
│   SKILL.md                      │    │   🛠️ 16 个 MCP 工具:             │
│   - 工具使用指南                 │    │   • 查询: tron_get_*()           │
│   - 工作流程示例                 │    │   • 租赁: tron_lease_*()         │
│   - 错误处理指导                 │    │   • 转账: tron_build/sign/broadcast │
│                                 │    │   • 闭环: tron_transfer()        │
└─────────────────────────────────┘    │   • 钱包: tron_get_wallet_info() │
         AI 读取学习                      │   • 安全: tron_check_account_safety │
                                          │   • 资源: tron_get_account_energy/bandwidth │
                                          └─────────────────────────────────┘
                        AI 调用执行 → 通过 MCP 协议调用工具
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
- ⚡ **资源租赁**：通过 TronZap API 租赁能量/带宽，降低转账手续费

## 快速开始

### 1️⃣ 克隆项目

从 GitHub 克隆本项目到本地：

```bash
git clone https://github.com/Neutralmilkzzz/MCPweb3.git
cd MCPweb3/tron-mcp-server
```

或直接下载 ZIP 压缩包并解压。

### 2️⃣ 一键安装配置（强烈推荐）

我们提供了全新的**全自动安装配置流程**，让您在 2 分钟内完成所有准备工作：

#### 步骤 1: 运行安装脚本

```powershell
# 在项目根目录运行
python install.py
```

或在 `tron-mcp-server` 子目录中运行：

```powershell
cd tron-mcp-server
python install.py
```

`install.py` 会自动完成：
- ✅ **Python 环境检查**（需 3.10+）
- ✅ **创建虚拟环境** `.venv`
- ✅ **安装所有依赖**（包括 `mcp`, `httpx`, `rich`, `questionary` 等）
- ✅ **注册 `tronmcp` 命令**到虚拟环境
- ✅ **显示操作指引**（下一步该做什么）

#### 步骤 2: 运行配置向导

安装完成后，运行交互式配置向导：

```bash
# Windows PowerShell
tron-mcp-server\.venv\Scripts\Activate.ps1
tronmcp onboard

# 或直接运行（无需手动激活）
tron-mcp-server\.venv\Scripts\tronmcp.exe onboard
```

`onboard` 向导提供 **6 步引导**，像支付宝一样简单：

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1️⃣ | 🌐 **选择网络** | 主网（真实交易）或 Nile 测试网（开发调试） |
| 2️⃣ | 🔐 **输入私钥** | 密码隐密输入，即时派生地址并校验 |
| 3️⃣ | 🔑 **配置 API Keys** | TronGrid + TronScan + TronZap（可选，带连接性测试） |
| 4️⃣ | 💾 **保存配置** | 自动写入 `.env` 文件并设置安全权限 |
| 5️⃣ | ⚙️ **添加到 PATH** | 可选，让 `tronmcp` 命令全局可用 |
| 6️⃣ | 🚀 **启动服务器** | 可选，立即启动 MCP Server（Stdio/SSE） |

> 💡 **提示**：`onboard` 会帮你完成所有配置，**无需手动编辑 `.env`**！

#### 步骤 3: 启动 MCP Server

配置完成后，根据你的客户端选择启动方式：

**方式一：Stdio 模式**（Claude Desktop、 Windsurf 等）

```bash
# 激活虚拟环境后
tronmcp server
# 或
python -m tron_mcp_server.server
```

**方式二：SSE 模式**（Cursor、Trae 等）

```bash
tronmcp server --sse
# 或
python -m tron_mcp_server.server --sse
```

默认监听 `http://127.0.0.1:8765/sse`，可通过 `MCP_PORT` 环境变量修改端口。

---

### 📋 环境要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows / macOS / Linux
- **网络**: 可访问 TRON 主网/测试网

---

### 🔧 手动配置（高级用户）

如果跳过 `onboard`，可手动创建 `.env` 文件：

```bash
# 复制示例文件
cp .env.example .env

# 编辑 .env，填写以下配置：
TRON_NETWORK=mainnet          # 或 nile（测试网）
TRON_PRIVATE_KEY=your_private_key_here  # 64位十六进制
TRONGRID_API_KEY=your_key     # 可选
TRONSCAN_API_KEY=your_key     # 可选
TRONZAP_API_TOKEN=your_token  # 可选，用于能量/带宽租赁
TRONZAP_API_SECRET=your_secret  # 可选，用于能量/带宽租赁
```

---

### 🚀 运行 MCP Server

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

### 资源租赁工具

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `tron_lease_energy` | 租赁 TRON 能量 (Energy)，降低 USDT 转账 Gas 费用 | `to_address`, `amount`, `duration` (1/24h), `activate_account` |
| `tron_lease_bandwidth` | 租赁 TRON 带宽 (Bandwidth)，降低转账数据存储费用 | `to_address`, `amount` |

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
│   ├── cli.py                # CLI 命令入口（tronmcp 命令）
│   ├── onboard.py            # 交互式配置向导（6 步引导）
│   ├── call_router.py        # 调用路由器
│   ├── skills.py             # 技能清单定义
│   ├── tron_client.py        # TRONSCAN REST 客户端（查询）
│   ├── trongrid_client.py    # TronGrid API 客户端（交易构建/广播）
│   ├── tx_builder.py         # 交易构建器（含安全检查）
│   ├── key_manager.py        # 本地私钥管理（签名/地址派生）
│   ├── validators.py         # 参数校验
│   ├── formatters.py         # 输出格式化
│   └── config.py             # 配置管理（含 TronZap API 配置）
├── Changelog.md              # 版本更新日志
├── test_known_issues.py      # 已知问题测试
├── test_transfer_flow.py     # 转账流程测试
├── test_tx_builder_new.py    # 交易构建测试
├── pyproject.toml            # 项目配置（依赖、脚本入口）
├── requirements.txt          # 依赖（备用）
└── .env.example              # 环境变量示例
```

## 🛠️ 开发与测试

### 运行测试

```bash
# 使用测试脚本（推荐）
python run_tests.py

# 或直接使用 pytest
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

---

## 🎨 新功能亮点

### 🚀 一键安装（install.py）

告别繁琐的手动配置！`install.py` 提供全自动安装体验：

```powershell
python install.py
```

**自动完成**：
- Python 环境检查
- 虚拟环境创建
- 依赖安装（包括 `mcp`, `httpx`, `rich`, `questionary`）
- `tronmcp` 命令注册
- 清晰的下一步指引

### 🎯 交互式配置（onboard）

`tronmcp onboard` 提供类似支付宝的交互体验：

- 🔐 **私钥隐密输入**：密码框显示，保护隐私
- 🧮 **即时地址校验**：输入私钥后立即派生地址，让用户确认
- 🌐 **网络选择**：主网/测试网一目了然
- 🔑 **API Keys 配置**：TronGrid + TronScan，带连接性测试
- 💾 **自动持久化**：配置自动保存到 `.env`，无需手动编辑
- 🎨 **品牌化 UI**：TRONMCP LOGO + 支付宝蓝主题色

### 💻 CLI 命令系统

安装后可使用 `tronmcp` 命令：

```bash
tronmcp onboard              # 运行配置向导
tronmcp server               # 启动 MCP Server（stdio）
tronmcp server --sse         # 启动 MCP Server（SSE）
tronmcp --help               # 查看帮助
```

---

## 🔧 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **查询 API**: TRONSCAN REST（余额、交易状态、Gas 参数、安全检查）
- **交易 API**: TronGrid（构建真实交易、广播签名交易）
- **签名算法**: ECDSA secp256k1 + RFC 6979 确定性签名
- **地址派生**: 私钥 → secp256k1 公钥 → Keccak256 → Base58Check
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）
- **关键依赖**: `mcp`, `httpx`, `ecdsa`, `pycryptodome`, `base58`, `rich`, `questionary`

---

## 📦 依赖管理

### 核心依赖（自动安装）

`install.py` 会自动安装以下核心包：

```txt
mcp>=1.0.0
httpx>=0.24.0
base58>=2.1.0
ecdsa>=0.18.0
pycryptodome>=3.19.0
python-dotenv>=1.0.0
uvicorn>=0.20.0
starlette>=0.27.0
sse-starlette>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
qrcode[pil]>=7.4.0
rich>=13.0.0
questionary>=2.0.0
tronzap-sdk>=0.1.0
```

### 可选依赖

如需完整功能（包括 `tronpy` 支持），可安装 extras：

```bash
pip install "tron-mcp-server[full]"
```

---

## ⚠️ 端口占用处理

服务器启动时会自动检测端口占用，如果默认端口 `8765` 被占用：

1. 设置环境变量 `MCP_PORT` 为其他可用端口：
   ```bash
   # Windows PowerShell
   $env:MCP_PORT=8766
   python -m tron_mcp_server.server --sse
   ```

2. 或修改 `.env` 文件：
   ```bash
   MCP_PORT=8766
   ```

---

## 🤝 配套 Agent Skill

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

---

## 📝 注意事项

- 🔐 **私钥安全**：私钥仅存储在本地 `.env` 文件中，绝不会上传到任何服务器
- 🌐 **网络选择**：主网用于真实交易，测试网用于开发调试，请根据需求选择
- 🔑 **API Keys**：TronGrid 和 TronScan API Keys 为可选配置，不配置也能使用基本功能
- 🛡️ **安全审计**：转账前会自动检查地址安全性（TRONSCAN 黑名单 + 多维风控）
- ⛽ **Gas 卫士**：自动拦截余额不足的"必死交易"，避免资产损失

---

## ❓ 常见问题

详见根目录 [README.md](../README.md#常见问题-faq) 中的完整 FAQ 部分。

---

## 📄 许可证

MIT

## 🔧 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **查询 API**: TRONSCAN REST（余额、交易状态、Gas 参数、安全检查）
- **交易 API**: TronGrid（构建真实交易、广播签名交易）
- **资源租赁 API**: TronZap（能量/带宽租赁服务）
- **签名算法**: ECDSA secp256k1 + RFC 6979 确定性签名
- **地址派生**: 私钥 → secp256k1 公钥 → Keccak256 → Base58Check
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）
- **关键依赖**: `mcp`, `httpx`, `ecdsa`, `pycryptodome`, `base58`, `rich`, `questionary`, `tronzap-sdk`

## 常见问题

参见根目录 [README.md](../README.md#常见问题-faq) 中的完整 FAQ 部分。

## 贡献

欢迎贡献！请查看根目录的 [贡献指南](../README.md#贡献指南)。

## 许可证

MIT
