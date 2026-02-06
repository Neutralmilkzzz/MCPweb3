# 更新日志

> 记录项目自启动以来的关键里程碑与主要变更，便于回溯与评审。

---

## 2026-02-06 (v1.0.2) — 上线前关键修复 + 工具精简与扩展

### 🔴 关键修复

#### 修复一：地址校验宽松漏洞 (validators.py)

- **问题**: `is_valid_address()` 对非 34 字符的 T 开头地址使用宽松校验（`len >= 20` 即通过），导致非法地址不被拦截，可能造成资金丢失
- **修复**: 删除宽松分支，Base58 地址严格要求 34 字符，不匹配直接返回 False

#### 修复二：新地址 TRX 余额查询异常 (tron_client.py)

- **问题**: `get_balance_trx()` 中 `_first_not_none()` 缺少兜底值 `0`，查询从未上链的新地址时抛出 `ValueError` 而非返回余额 0
- **修复**: 添加兜底参数 `0`，与 `get_account_status()` 和 `get_account_tokens()` 保持一致

### 近期合并的 PR 汇总

- **PR #39**: 解决合并冲突，修复中文错误消息断言
- **PR #37**: 新增 `tron_sign_tx`、`tron_get_internal_transactions`、`tron_get_account_tokens` 三个 MCP 工具
- **PR #36**: 新增精简版 MCP 工具集测试覆盖
- **PR #35**: 移除冗余的组合工具，精简 MCP Server 工具列表
- **PR #34**: 修复未使用的 Optional 导入、模块级 json 导入、货币转换浮点精度问题

---

## 2026-02-06 (交易历史查询) — 新增交易历史查询功能

### ✅ 新增功能：`tron_get_transaction_history` 工具

- **功能描述**: 支持查询指定 TRON 地址的交易历史记录
- **支持筛选**:
  - `token=None`: 查询所有类型交易（合并 TRX + TRC20）
  - `token="TRX"`: 仅查询 TRX 原生转账
  - `token="USDT"`: 仅查询 USDT (TRC20) 转账
  - `token=<合约地址>`: 查询指定 TRC20 代币的转账记录
- **支持分页**: `limit`（最大 50 条）和 `start`（偏移量）参数
- **返回字段**: `txid`, `from`, `to`, `amount`, `token`, `direction`（IN/OUT/SELF）, `timestamp`
- **关联代码**:
  - `server.py`: MCP 工具 `tron_get_transaction_history` 注册
  - `call_router.py`: `_handle_get_transaction_history()` 路由处理
  - `tron_client.py`: `get_transfer_history()` / `get_trc20_transfer_history()` API 调用
  - `formatters.py`: `format_transaction_history()` 输出格式化

### ✅ 新增测试文件

- `test_transaction_history.py`: 交易历史查询功能测试用例覆盖

### ✅ 文档更新

- `README.md`: 在架构图、特性列表、MCP 工具列表和项目结构中新增交易历史查询工具的说明（中英文同步更新）

---

## 2026-02-06 (深夜) — 错误消息优化 + 结构统一 + 配置文件补全

### ✅ 改进一：`load_private_key()` 错误消息精简 (key_manager.py)

- **修复前**: 未配置私钥时抛出多行错误消息（含换行符），信息冗长
- **修复后**: 合并为单行消息，保留所有关键信息（环境变量名、格式要求）
- **效果**: 日志和 API 响应中的错误消息更易读，不影响排错能力

### ✅ 改进二：`check_sender_balance` 错误对象结构统一 (tx_builder.py)

- **修复前**: USDT 不足使用 `required/available`，Gas 和 TRX 不足仅有 `required_sun/available_sun`，字段不统一
- **修复后**: 所有错误类型均包含统一的 `required/available`（人类可读单位）和 `required_sun/available_sun`（精确 SUN 单位）字段
- **效果**: 消费方（LLM、前端）无需按错误类型做特殊处理，统一读取 `required/available` 即可

### ✅ 改进三：`.env.example` 配置文件补全

- 新增 `TRON_PRIVATE_KEY` 配置说明（签名/广播必需）
- 新增 Gas 费用估算参数：`ESTIMATED_USDT_ENERGY`、`ENERGY_PRICE_SUN`、`MIN_TRX_TRANSFER_FEE`、`FREE_BANDWIDTH_DAILY`、`USDT_BANDWIDTH_BYTES`、`BANDWIDTH_PRICE_SUN`
- 按功能分组（私钥、API、服务、合约、Gas），提升可读性

### ✅ 改进四：修复 `KeyManager` 类缺失 (key_manager.py)

- `call_router.py` 引用了 `KeyManager` 类但该类不存在，导致所有测试无法运行
- 新增 `KeyManager` 类封装 `is_configured()` 和 `sign_transaction()` 方法

### ✅ 新增测试文件

- `test_error_messages.py`: 7 个测试用例
  - `TestKeyManagerErrorMessages`: 错误消息单行化、信息完整性
  - `TestCheckSenderBalanceErrorStructure`: 所有错误类型字段统一性验证

---

## 2026-02-06 (晚间) — 关键 Bug 修复：API 认证 + 环境变量加载

### 🔴 紧急修复：安全检查在 MCP 服务器中完全失效

经实际端到端测试发现，尽管下午的代码逻辑修复全部正确，但在通过 MCP 客户端调用时，安全检查始终返回 `Unknown / 无法验证`。排查后发现两个致命的工程配置问题：

#### Bug 1：API Header 名称错误 (tron_client.py)

| 项目 | 修复前 | 修复后 |
|:---:|:---|:---|
| Header | `TRONSCAN-API-KEY` | `TRON-PRO-API-KEY` |
| 结果 | TRONSCAN API 返回 **401 Unauthorized** | API 正常返回 200 |

- **影响**: 所有需要 API Key 的接口（accountv2、security）全部 401 失败
- **表现**: `check_account_risk()` 两个 API 都进 `except` → `risk_type = "Unknown"` 
- **验证地址**: `TEd8bfCniiWoZNrDnSCxKYS3aRyQuChy9Q`（应为 Suspicious + Fraud History，修复前返回 Unknown）

#### Bug 2：`.env` 文件未被加载 (server.py)

| 项目 | 修复前 | 修复后 |
|:---:|:---|:---|
| `server.py` | 无 `import config` | 增加 `from . import config` |
| 结果 | `os.getenv("TRONSCAN_API_KEY")` 始终为空 | `.env` 中的 API Key 正确加载 |

- **根因**: `config.py` 中有 `load_dotenv()`，但 `server.py` 从未 import 它，导致 MCP 服务器进程启动时 `.env` 文件未被读取
- **为何终端测试能通过**: 终端手动测试时会显式调用 `from dotenv import load_dotenv; load_dotenv()`

#### Bug 3：带宽费估算逻辑修正 (tx_builder.py)

- **修复前**: `estimated_fee = energy_fee - free_bw_savings`（错误地从能量费中减去带宽节省）
- **修复后**: `estimated_fee = energy_fee + actual_bw_fee`（能量费和带宽费分开计算，免费带宽仅覆盖带宽部分）
- **阈值变化**: 27.3 TRX（纯能量费）+ 0 TRX（带宽被免费额度覆盖）= **27.3 TRX**

#### 其他改进

- `formatters.py`: `risk_type` 为 `Unknown` 或 `Partially Verified` 时，`is_safe` 不再返回 `True`
- `.gitignore`: 增加 `.roo/`、`EVALUATION_REPORT.md`、`Tasks` 等内部文件的忽略规则
- 从 git 追踪中移除 `.roo/mcp.json`、`EVALUATION_REPORT.md`、`Tasks`

---

## 2026-02-06 (下午) — 四大安全缺陷修复

### 安全关键修复：风险检测、熔断逻辑、手续费估算与工程化 (Critical Security Fixes)

本次更新 **完整修复** 了审计中暴露的四大类问题，将系统从"演示级"推至"生产级"安全标准。每项修复均有对应测试用例验证。

---

#### ✅ 修复一：信誉案底查杀缺失 — Reputation Gap (tron_client.py)

- **问题本质**: 此前因 `rep_tag` 报错回滚后，风险检测仅依赖 `redTag`（官方红标）。大量"有案底但无红标"的地址（如三年前标记为 Suspicious 的老骗子）被漏检，产生严重的 **False Negative**。
- **修复方案**: 在 `check_account_risk()` 中实现 **双层多指标深度体检**：
  - **Layer 1 — AccountV2 API** (标签 + 投诉):
    - `redTag` → 🔴 高危标签
    - `greyTag` → ⚪ 灰度存疑（如 Suspicious）
    - `publicTag` → 关键词匹配 (`suspicious`, `hack`, `scam`)
    - `feedbackRisk` → ⚠️ 用户投诉
  - **Layer 2 — Security Service API** (黑产行为):
    - `is_black_list` → 💀 USDT/稳定币黑名单
    - `has_fraud_transaction` → 💸 欺诈交易记录
    - `fraud_token_creator` → 🪙 假币创建者
    - `send_ad_by_memo` → 📢 垃圾广告账号
- **效果**: 即使 `redTag` 为空，只要存在 `greyTag: Suspicious` 或 `has_fraud_transaction: True`，AI 仍会正确报告风险，消除 False Negative。
- **关联代码**: [check_account_risk()](tron-mcp-server/tron_mcp_server/tron_client.py#L248-L408)

---

#### ✅ 修复二：API 频率限制与静默失效 — Silent Failure Elimination (tron_client.py + tx_builder.py)

- **问题本质**: `except Exception as e: return {"is_risky": False}` — 当网络断开、API 返回 429/403、或代码自身 Bug 时，系统 **静默返回"安全"**，这在金融安全工具中是致命缺陷。
- **修复方案 — 三级降级策略**:
  1. **两个 API 都失败**: `risk_type = "Unknown"`，附带提示 *"⚠️ 安全检查服务不可用，无法验证地址安全性，请谨慎操作"*。**不再声称地址安全。**
  2. **仅一个 API 失败**: `risk_type = "Partially Verified"`，明确告知只完成了部分检查。
  3. **`check_recipient_security()` 异常捕获**: 安全检查本身异常时，返回 `risk_type: "Unknown"` + `degradation_warning`，而非默认放行。
- **变量初始化安全 (防 UnboundLocalError)**:
  - 所有风险变量在函数顶部显式初始化:
    ```python
    red_tag = ""
    grey_tag = ""
    feedback_risk = False
    is_black_list = False
    # ... 共 9 个变量
    ```
  - 使用 `v2_success` / `sec_success` 布尔标志追踪每个 API 的成功状态，彻底消除作用域陷阱。
- **效果**: 网络故障 / API 限流 / 代码异常时，系统明确告知"无法判定"，将风险决策权交还用户。
- **关联代码**: [降级策略](tron-mcp-server/tron_mcp_server/tron_client.py#L389-L404), [check_recipient_security()](tron-mcp-server/tron_mcp_server/tx_builder.py#L357-L386)

---

#### ✅ 修复三：手续费估算接入免费带宽动态抵扣 — Free Bandwidth Deduction (tx_builder.py)

- **问题本质**: USDT 转账手续费一刀切按 `65000 Energy × 420 SUN = 27.3 TRX` 估算，未考虑 TRON 网络每地址每天 **600 免费带宽点**。对余额在 26.95~27.30 TRX 之间的边界用户，会被误报"余额不足"。
- **修复方案**: 在 `check_sender_balance()` 中正确分离能量费与带宽费计算:
  ```python
  FREE_BANDWIDTH_DAILY = 600        # 每地址每天免费带宽
  USDT_BANDWIDTH_BYTES = 350        # USDT Transfer 消耗带宽
  BANDWIDTH_PRICE_SUN = 1000        # 每带宽点 SUN 价格
  
  # 能量费（固定，免费带宽无法抵扣）
  energy_fee_sun = ESTIMATED_USDT_ENERGY * ENERGY_PRICE_SUN  # 27.3 TRX
  # 带宽费（免费 600 点覆盖 350 字节消耗 → 0 TRX）
  free_bw_coverage = min(USDT_BANDWIDTH_BYTES, FREE_BANDWIDTH_DAILY)
  actual_bw_fee_sun = max(0, (USDT_BANDWIDTH_BYTES - free_bw_coverage) * BANDWIDTH_PRICE_SUN)
  estimated_fee_sun = energy_fee_sun + actual_bw_fee_sun  # 27.3 TRX
  ```
- **效果**: 能量费与带宽费分开计算，免费带宽仅覆盖带宽部分。实际阈值 27.3 TRX，带宽费完全被免费额度覆盖。所有参数可通过环境变量覆盖。
- **关联代码**: [带宽抵扣逻辑](tron-mcp-server/tron_mcp_server/tx_builder.py#L157-L165), [参数声明](tron-mcp-server/tron_mcp_server/tx_builder.py#L147-L155)

---

#### ✅ 修复四：交易状态回执 + 工程化兜底 — Transaction Confirmation & Safety Net (tron_client.py + server.py)

- **交易确认查询**:
  - **问题**: 用户转账后问"钱到了吗？"，AI 无法回答。
  - **修复**: 实现 `get_transaction_status(txid)` 通过 `transaction-info?hash={hash}` 接口查询交易确认状态，区分 SUCCESS / REVERT / Pending 三种场景。
  - MCP 工具 `tron_get_transaction_status` 已注册，AI 可直接调用。
  - **关联代码**: [get_transaction_status()](tron-mcp-server/tron_mcp_server/tron_client.py#L192-L208)

- **熔断机制交互完善 (force_execution)**:
  - **问题**: `force_execution` 参数的拦截信息若写得不够清晰，LLM 可能陷入"对不起我不能转"的死循环。
  - **修复**: 拦截信息中包含明确的重试指令:
    > *"如果您必须转账，请明确告知'强制执行'，或在工具调用中设置 force_execution=True。"*
  - 返回结构化数据 (`blocked`, `risk_reasons`, `security_check`)，LLM 可精确解析并决策。
  - **关联代码**: [熔断拦截信息](tron-mcp-server/tron_mcp_server/tx_builder.py#L472-L491)

- **异常捕获治理**:
  - **问题**: 宽泛的 `except Exception` 导致所有错误（网络断开、代码 Bug、API 挂掉）统一静默为"安全"。
  - **修复**: 移除所有"静默安全"的兜底，替换为语义明确的降级响应（`Unknown` / `Partially Verified` / `degradation_warning`）。

---

### 修复总结

| 问题编号 | 问题类型 | 修复前行为 | 修复后行为 | 风险等级 |
|:---:|:---|:---|:---|:---:|
| 1 | 信誉案底漏检 | 仅查 redTag，灰标/案底地址报安全 | 9 维指标全覆盖，Suspicious 地址被正确检出 | 🔴 严重 |
| 2 | API 故障静默安全 | 网络断 / 429 限流 → 返回 Safe | 返回 Unknown + 降级警告，不再声称安全 | 🔴 严重 |
| 3 | 手续费估算一刀切 | 无免费带宽抵扣，边界用户被误拒 | 动态扣除 0.35 TRX 免费额度，边界用户放行 | 🟡 中等 |
| 4 | 缺少交易回执 | 转账后无法查询确认状态 | `get_transaction_status` 支持链上确认查询 | 🟢 体验 |

---

## 2026-02-06 (上午)

### 已知问题审计与测试覆盖 (Known Issues Audit & Test Coverage)

本次更新针对项目中已识别的 **四大类问题** 进行了系统性审计，并编写了 30+ 测试用例覆盖这些场景。核心目的：在 Hackathon 演示前暴露所有潜在 False Negative 和静默失效风险。

#### 🔴 问题一：风险检测模块 — 信誉案底查杀缺失 (Reputation Gap)

- **位置**: `tron_client.py` → `check_account_risk()`
- **现状**: `redTag` 为空但 `greyTag` 含 `Suspicious`、`publicTag` 含 `hack/scam`、`feedbackRisk=True` 的地址 **已能被检出**（当前实现已覆盖）
- **已验证**: 多个非 redTag 风险指标（greyTag、publicTag、feedbackRisk、has_fraud_transaction）均被正确检测
- **遗留风险**: `reputation.tag`（Tronscan V1 字段）的 Suspicious 标签在 V2 API 中如何映射仍需确认

#### 🔴 问题二：API 频率限制与静默失效 (Rate Limiting & Silent Failure)

- **位置**: `tron_client.py` → `check_account_risk()` 的 `except Exception` 块
- **问题**: 当两个安全 API（accountv2 + security）**同时失败**时（429 频率限制、网络断开等），代码返回 `is_risky=False, risk_type="Safe"`
- **风险等级**: 🔴 **严重** — 金融安全工具中"静默失效"是最危险的缺陷
- **改善方向**:
  1. 当两个 API 都失败时，`risk_type` 应设为 `"Unknown"` 或 `"Unable to verify"`
  2. 添加"降级提示"：`"⚠️ 安全检查服务暂时不可用，请谨慎操作"`
  3. 在 `check_recipient_security()` 中，API 失败时考虑不默认放行
- **测试覆盖**: `test_both_apis_fail_should_not_claim_safe`, `test_api_returns_429_rate_limit`

#### 🟡 问题三：熔断机制交互逻辑 (Circuit Breaker Interaction)

- **位置**: `tx_builder.py` → `build_unsigned_tx()`, `server.py` → `tron_build_tx()`
- **现状**: `force_execution` 参数已实现，拦截信息结构清晰（含 `blocked`, `summary`, `risk_reasons`, `security_check`）
- **已验证**: 
  - 风险地址 + `force_execution=False` → 交易被拦截 ✅
  - 风险地址 + `force_execution=True` → 交易被构建 ✅
  - 拦截信息包含 `force_execution=True` 的操作提示 ✅
- **改善方向**: 在 SKILL.md 中加强对 LLM 的提示，明确"只有用户说了'强制'才能设置 `force_execution=True`"

#### 🟡 问题四：手续费估算误差 — 免费带宽未抵扣 (Free Bandwidth Gap)

- **位置**: `tx_builder.py` → `check_sender_balance()`
- **问题**: USDT 转账手续费固定按 `65000 Energy × 420 SUN = 27.3 TRX` 估算，未接入 TRON 网络每地址每天 600 免费带宽的动态抵扣
- **影响**: 
  - USDT 转账带宽消耗约 350 bytes，免费带宽可节省约 0.35 TRX
  - 对于余额在 26.95~27.30 TRX 之间的用户，可能被误报"余额不足"
- **风险等级**: 🟡 中等 — 边界用户会被错误拒绝，但不会导致资金损失
- **改善方向**: 查询用户当前剩余免费带宽，动态调整 Gas 估算

#### 🟢 问题五：缺乏交易状态回执 (Transaction Confirmation)

- **位置**: `tron_client.py` → `get_transaction_status()`
- **现状**: 功能已实现，通过 `transaction-info?hash={hash}` 接口查询
- **已验证**: call_router 中的 `get_transaction_status` 路由工作正常，支持成功/pending/无效 txid 三种场景
- **改善方向**: 考虑在 SKILL.md 中增加"转账后查询确认"的推荐工作流

#### 新增测试文件

- **`test_known_issues.py`**: 30+ 测试用例，覆盖上述所有问题
  - `TestReputationGap`: 信誉案底测试（greyTag, publicTag, feedbackRisk, fraud history, 多指标叠加）
  - `TestAPIFailureSafety`: API 失败时的行为审计
  - `TestVariableInitialization`: 变量初始化安全性（防 UnboundLocalError）
  - `TestCircuitBreakerLogic`: 熔断机制完整性
  - `TestBlockedResponseParsability`: 拦截信息可解析性
  - `TestCallRouterIntegration`: 路由层错误处理
  - `TestFeeEstimation`: 手续费估算边界测试
  - `TestRecipientSecurityFallback`: 安全检查降级测试
  - `TestTransactionConfirmation`: 交易状态回执测试
  - `TestExceptionHandlingAudit`: 异常捕获审计
  - `TestFormatterSafety`: 格式化函数降级测试
  - `TestCheckAccountSafetyEndToEnd`: 端到端安全检查测试

---

## 2026-02-05

### 核心特性：Gas 优化与交易安全性

本次迭代重点针对 **Gas 优化 (Gas Optimization)** 和 **交易安全性 (Transaction Safety)** 进行了重大升级，后端模块现已具备生产级 (Production-Ready) 的防错能力。

#### 1. 新增特性：安全审计 (Security Audit / Anti-Fraud)

- **模块位置**:
  - `tron_mcp_server/tron_client.py` → `check_account_risk`（底层 API 调用）
  - `tron_mcp_server/tx_builder.py` → `check_recipient_security`（业务逻辑封装）
- **功能描述**: 集成 TRONSCAN 官方黑名单 API，在构建交易前识别接收方地址是否被标记为恶意地址
- **数据源**: TRONSCAN `https://apilist.tronscanapi.com/api/multiple/chain/query`，检查 `redTag` 字段
- **风险类型**: 支持识别 Scam（诈骗）、Phishing（钓鱼）等多种恶意标记
- **安全措施**:
  - `risk_type` 经过清洗处理（仅保留字母数字和空格，最大 50 字符），防止注入攻击
  - API 调用失败时返回 `is_risky: False`，避免阻塞正常交易
- **返回结构**:
  ```python
  # 检测到恶意地址时
  result["security_warning"]  # "⛔ 严重安全警告: 接收方地址被 TRONSCAN 标记为 【Scam】。转账极可能导致资产丢失！"
  result["security_check"]    # {"checked": True, "is_risky": True, "risk_type": "Scam", "detail": "..."}
  ```
- **价值**: 在交易构建阶段预警用户，避免向已知恶意地址转账导致资产损失

#### 2. 新增特性：Gas 卫士 (Gas Guard / Anti-Revert)

- **模块位置**: `tron_mcp_server/tx_builder.py` → `check_sender_balance`
- **功能描述**: 在构建交易前，强制检查发送方的余额状态
- **逻辑**: 
  - 不仅检查转账代币（如 USDT）是否充足
  - 还预估并检查 TRX 余额是否足够支付网络手续费（Estimated Gas）
- **价值**: 从源头拦截"必死交易"，防止因余额不足导致交易上链失败（Revert）而白白浪费 Gas

#### 3. 新增特性：接收方状态检测 (Recipient Status Check)

- **模块位置**:
  - `tron_mcp_server/tron_client.py` → `get_account_status`（底层支持）
  - `tron_mcp_server/tx_builder.py` → `check_recipient_status`（业务逻辑）
- **功能描述**: 在构建 USDT 转账交易时，自动识别接收方地址是否为"未激活"状态
- **价值**: 提示用户向未激活账户转账会有额外的高额能量消耗（Energy Cost for Account Creation），避免意外的高成本支出

#### 4. 用户体验优化：交易有效期延长 (Expiration Extension)

- **模块位置**: `tron_mcp_server/tx_builder.py`
- **变更**: 将交易的 `expiration` 时间从 1 分钟 (60s) 延长至 **10 分钟 (600s)**
- **原因**: 考虑到 Hackathon 演示及人工签名的延迟，留出更充足的时间窗口，防止交易在签名或广播前超时失效

#### 5. 架构决策：轻量级 TxID

- **说明**: 确认保留使用 `hashlib.sha256` 生成本地临时 txID 的方案
- **原因**: 作为未签名交易构建器 (Unsigned Tx Builder)，此方案在保证唯一性的前提下避免了引入沉重的 protobuf 依赖，符合 Hackathon 项目轻量化、快速迭代的要求

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
