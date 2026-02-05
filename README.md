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
- [更新日志](#更新日志)
- [技术细节](#技术细节)
- [常见问题 FAQ](#常见问题-faq)
- [贡献指南](#贡献指南)
- [许可证](#许可证)

## 架构

本项目采用 **Agent Skill + MCP Server 分离架构**：

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   tron-blockchain-skill/        │    │   tron-mcp-server/              │
│   (Agent Skill - 知识层)         │    │   (MCP Server - 执行层)          │
│                                 │    │                                 │
│   SKILL.md                      │    │   tron_get_usdt_balance()       │
│   - 教 AI 如何使用工具           │    │   tron_get_balance()            │
│   - 工作流程示例                 │    │   tron_get_gas_parameters()     │
│   - 错误处理指导                 │    │   tron_get_transaction_status() │
│                                 │    │   tron_build_tx()               │
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

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `tron_get_usdt_balance` | 查询 USDT 余额 | `address` |
| `tron_get_balance` | 查询 TRX 余额 | `address` |
| `tron_get_gas_parameters` | 获取 Gas 参数 | 无 |
| `tron_get_transaction_status` | 查询交易状态 | `txid` |
| `tron_get_network_status` | 获取网络状态 | 无 |
| `tron_build_tx` | 构建未签名交易 | `from_address`, `to_address`, `amount`, `token` |

## 项目结构

```
.
├── tron-blockchain-skill/    # Agent Skill（知识层）
│   ├── SKILL.md              # AI 读取的技能说明
│   └── LICENSE.txt
├── tron-mcp-server/          # MCP Server（执行层）
│   ├── tron_mcp_server/      # Python 包
│   ├── requirements.txt      # 依赖
│   └── .env.example          # 环境变量示例
├── Changelog.md              # 更新日志
└── README.md                 # 本文件
```

## 更新日志

请参阅 [Changelog.md](Changelog.md) 获取最新记录。

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **API**: TRONSCAN REST
- **主要接口**: account, chainparameters, transaction-info, block
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）

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
A: `build_tx` 工具仅生成未签名交易，需要用户使用私钥管理工具（如 TronLink、硬件钱包）在本地签名，然后通过 TRON 节点广播。

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

## 🚧 待完成工作

### 1. Agent Skill 全流程优化（高优先级）

当前 `tron-blockchain-skill/SKILL.md` 仅提供了基础的工具说明，尚需进行全面优化：

- [ ] **多步骤工作流编排**：补充完整的转账全流程示例（余额检查 → Gas 估算 → 交易构建 → 提示签名）
- [ ] **上下文感知**：优化 Skill 以支持 AI 在多轮对话中保持状态
- [ ] **错误恢复指导**：为每种错误类型提供详细的恢复策略和用户引导话术
- [ ] **安全提示增强**：在涉及资产操作时，强化风险提示和确认流程
- [ ] **示例对话补充**：添加更多真实场景的对话示例，帮助 AI 理解意图

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
- [Changelog](#changelog-en)
- [Technical Details](#technical-details-en)
- [FAQ](#faq-en)
- [Contributing](#contributing-en)
- [License](#license-en)

<a name="architecture-en"></a>

## Architecture

This project uses an **Agent Skill + MCP Server separation architecture**:

```
┌─────────────────────────────────┐    ┌─────────────────────────────────┐
│   tron-blockchain-skill/        │    │   tron-mcp-server/              │
│   (Agent Skill - Knowledge)     │    │   (MCP Server - Execution)      │
│                                 │    │                                 │
│   SKILL.md                      │    │   tron_get_usdt_balance()       │
│   - Teach AI how to use tools   │    │   tron_get_balance()            │
│   - Workflow examples           │    │   tron_get_gas_parameters()     │
│   - Error handling guidance     │    │   tron_get_transaction_status() │
│                                 │    │   tron_build_tx()               │
└─────────────────────────────────┘    └─────────────────────────────────┘
         AI reads and learns                     AI calls and executes
```

<a name="features-en"></a>

## Features

- 🔧 **Standard MCP Tools**: `tron_*` prefix, following MCP best practices
- 📚 **Agent Skill Support**: Separate SKILL.md teaches AI how to use the tools
- 💰 **USDT/TRX Balance Query**: Query TRC20 and native token balances
- ⛽ **Gas Parameters**: Get current network gas prices
- 📊 **Transaction Status**: Query transaction confirmation status
- 🏗️ **Transaction Building**: Build unsigned USDT/TRX transfer transactions

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
# Edit .env file to configure TRONSCAN API as needed
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

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `tron_get_usdt_balance` | Query USDT balance | `address` |
| `tron_get_balance` | Query TRX balance | `address` |
| `tron_get_gas_parameters` | Get Gas parameters | None |
| `tron_get_transaction_status` | Query transaction status | `txid` |
| `tron_get_network_status` | Get network status | None |
| `tron_build_tx` | Build unsigned transaction | `from_address`, `to_address`, `amount`, `token` |

<a name="project-structure-en"></a>

## Project Structure

```
.
├── tron-blockchain-skill/    # Agent Skill (Knowledge layer)
│   ├── SKILL.md              # Skill documentation for AI
│   └── LICENSE.txt
├── tron-mcp-server/          # MCP Server (Execution layer)
│   ├── tron_mcp_server/      # Python package
│   ├── requirements.txt      # Dependencies
│   └── .env.example          # Environment variables example
├── Changelog.md              # Update log
└── README.md                 # This file
```

<a name="changelog-en"></a>

## Changelog

See [Changelog.md](Changelog.md) for the latest updates.

<a name="technical-details-en"></a>

## Technical Details

- **USDT Contract**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 decimals)
- **API**: TRONSCAN REST
- **Main Endpoints**: account, chainparameters, transaction-info, block
- **Transport Protocol**: stdio (default) / SSE (`--sse` startup)
- **Default Port**: 8765 (SSE mode, configurable via `MCP_PORT` environment variable)

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
A: The `build_tx` tool only generates unsigned transactions. Users need to sign with private key management tools (like TronLink, hardware wallets) locally, then broadcast through TRON nodes.

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

## 🚧 TODO

### 1. Agent Skill Complete Workflow Optimization (High Priority)

The current `tron-blockchain-skill/SKILL.md` only provides basic tool descriptions and needs comprehensive optimization:

- [ ] **Multi-step workflow orchestration**: Complete transfer workflow examples (balance check → gas estimation → transaction building → sign prompt)
- [ ] **Context awareness**: Optimize Skill to support AI state maintenance across multiple conversation rounds
- [ ] **Error recovery guidance**: Provide detailed recovery strategies and user guidance for each error type
- [ ] **Enhanced security prompts**: Strengthen risk warnings and confirmation processes for asset operations
- [ ] **Example dialogue additions**: Add more real-scenario dialogue examples to help AI understand intent

---

## Acknowledgments

Thanks to [Anthropic](https://www.anthropic.com/) for developing the MCP protocol, and the TRON ecosystem for their support.

---

<a name="license-en"></a>

## License

MIT License - See [LICENSE](LICENSE) file for details
