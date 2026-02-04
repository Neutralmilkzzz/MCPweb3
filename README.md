# TRON MCP Server

为 AI Agent 提供 TRON 区块链操作能力的 MCP Server，遵循 MCP 最佳实践。

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

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **API**: TRONSCAN REST
- **主要接口**: account, chainparameters, transaction-info, block
- **传输协议**: stdio（默认）/ SSE（`--sse` 启动）
- **默认端口**: 8765（SSE 模式，可通过 `MCP_PORT` 环境变量修改）

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

## 许可证

MIT
