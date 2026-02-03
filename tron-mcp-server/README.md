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

### 1. 安装依赖

```bash
cd tron-mcp-server
python -m venv .venv
.
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件，按需配置 TRONSCAN API
```

### 3. 运行 MCP Server

```bash
python -m tron_mcp_server.server
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
│   ├── __init__.py       # 包入口
│   ├── server.py         # MCP Server（暴露 tron_* 工具）
│   ├── call_router.py    # 调用路由器
│   ├── skills.py         # 内部技能定义
│   ├── tron_client.py    # TRONSCAN REST 客户端
│   ├── tx_builder.py     # 交易构建器
│   ├── validators.py     # 参数校验
│   ├── formatters.py     # 输出格式化
│   └── config.py         # 配置管理
├── tests/                # 测试用例（36 个测试）
├── requirements.txt      # 依赖
└── .env.example          # 环境变量示例
```

## 开发

### 运行测试

```bash
python -m pytest tests/ -v
```

### 测试覆盖

- ✅ 技能 Schema 验证
- ✅ 路由器功能测试
- ✅ TRONSCAN 客户端解析
- ✅ 交易构建
- ✅ 参数校验
- ✅ 格式化输出
- ✅ 错误处理

## 技术细节

- **USDT 合约**: `TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t` (TRC20, 6 位小数)
- **API**: TRONSCAN REST
- **主要接口**: account, chain/parameters, transaction-info, block

## 许可证

MIT
