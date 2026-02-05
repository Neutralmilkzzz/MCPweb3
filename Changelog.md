# 更新日志

> 记录项目自启动以来的关键里程碑与主要变更，便于回溯与评审。

---

## 2026-02-05

### 文档更新
- **README**：补充更新日志入口，新增中英双语 Changelog 引导。
- **Changelog**：新增本次文档更新记录，便于追踪。

---

## 2026-02-04

### 缺陷修复
- **TRON 客户端修复**：
  - 修复 `get_gas_parameters` 接口路径：将错误的 `chain/parameters` 修正为有效的 `chainparameters`。
  - 修复数据解析逻辑：适配 TRONSCAN API 返回的 `tronParameters` 根键，解决了无法获取能量费用（Gas）参数的问题。
- **技能同步**：
  - 根据 `tron-mcp-server` 的最新动作名称和参数，更新了 `tron-blockchain-skill/SKILL.md`，确保 AI Agent 能准确调用 `call(action, params)`。

### 项目优化
- **环境隐藏**：将其余测试代码文件夹 `tests` 重命名为 `.tests` 以进行平衡隐藏，减少开发环境视觉干扰。
- **Git 忽略配置**：
  - 新增 `.gitignore` 文件。
  - 将项目管理相关文件（`Tasks/`, `PRD.md`, `Questions*.md`, `*-Report.md` 等）设为忽略，防止非生产代码上传至 GitHub 仓库。
- **SSE 服务部署验证**：
  - 在服务器上验证了 SSE 模式运行，修正了端口占用的问题，成功在 `http://127.0.0.1:8766/sse` 启动。
- **可复现性优化**：
  - 更新 `requirements.txt`：补充 SSE 依赖 (starlette, sse-starlette)、Pydantic 依赖、添加 Python 版本说明。
  - 更新 `README.md`：修复 activate 命令错误、区分 Windows/Unix 安装步骤、添加详细的 Cursor 配置说明、添加端口占用提示。
- **技能逻辑统一**：
  - 更新 `skills.py` 模块，新增版本号并结构化技能清单。
  - 统一 `call_router.py` 的技能分发逻辑，支持更完整的“渐进式披露”。

---

## 2026-02-03

### 里程碑
- 完成 TRON MCP Server 全量实现并通过测试（56/56）。
- 完成 Agent Skill 与 MCP 彻底解耦架构。
- 形成评审与交付文档体系。
- 增加高级边界测试，用于暴露链上协议正确性风险。

### 文档交付
- PRD（老板版 / 开发版）完成并更新。
- 问题清单（含 39 问 Q&A）完成。
- 任务完成情况报告完成。
- 代码审阅报告完成。
- 新增专业评审问题清单2。

### 代码实现
- MCP 工具：
  - tron_get_usdt_balance
  - tron_get_balance
  - tron_get_gas_parameters
  - tron_get_transaction_status
  - tron_get_network_status
  - tron_build_tx
- TRON 客户端封装：切换为 TRONSCAN REST（account / chain/parameters / transaction-info / block）。
- 未签名交易构建（TRX 与 USDT），含 ref_block 与过期时间。
- 校验与格式化：地址/txid/金额校验；自然语言摘要。

### 配置与文档
- .env 示例更新为 TRONSCAN_API_URL / TRONSCAN_API_KEY。
- README 增加虚拟环境与依赖安装步骤。

### 架构调整
- 由“内置 Skill”转为“独立 Skill”（SKILL.md 与 MCP 并行）。
- MCP 工具命名统一为 tron_* 前缀。

### 测试新增
- 36 个基础测试全部通过。
- 新增高级边界测试（test_protocol_edge_cases.py）：
  - Base58→Hex 转换的正确性
  - TRC20 ABI 左填充编码
  - txid 边界长度
  - 地址前缀与长度严格性
  - pending 交易回执
  - 大数/精度边界
  - 最小金额/负数金额

### 风险提醒
- 代码审阅指出链上正确性风险（Base58→Hex 转换、ABI 编码填充等）需优先修复。

---

## 历史回溯（摘要）

- 需求梳理 → PRD → Q&A → 测试先行 → 代码实现 → 修复测试 → 架构分离（Skill / MCP） → 文档补全 → 专业审阅与边界测试。
