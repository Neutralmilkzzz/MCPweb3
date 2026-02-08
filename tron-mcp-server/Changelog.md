# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- � **全新一键安装体验**：`install.py` 脚本实现全自动环境搭建
  - 自动检测 Python 版本（需 3.10+）
  - 自动创建虚拟环境 `.venv`
  - 自动安装所有依赖并注册 `tronmcp` 命令
  - 跨平台支持（Windows/macOS/Linux）
  - 清晰的后续操作指引
- 🎯 **交互式配置向导**：`tronmcp onboard`（6 步引导）
  - Step 1/6: 网络选择（主网/mainnet 或 Nile 测试网）
  - Step 2/6: 私钥配置（密码隐密输入 + 即时地址派生校验）
  - Step 3/6: API Keys 配置（TronGrid + TronScan + 连接性测试）
  - Step 4/6: 持久化 `.env` 配置（自动设置文件权限）
  - Step 5/6: 自动添加 `tronmcp` 到 PATH（可选）
  - Step 6/6: 启动 MCP 服务器（Stdio/SSE/跳过）
- 🎨 **支付宝风格 CLI**：使用 `rich` 和 `questionary` 打造专业交互体验
  - TRONMCP 品牌标识（LOGO + 欢迎面板）
  - 蓝色主题配色（#1677FF）
  - 进度指示和状态图标（✅ ❌ ⏳）
- 🔄 **智能端口管理**：服务器启动时自动检测端口占用，支持自动重启
- 🐙 **CLI 命令系统**：`tronmcp` 命令统一入口
  - `tronmcp onboard` - 运行配置向导
  - `tronmcp --help` - 查看帮助信息

### Changed
- 更新 README.md，突出 `install.py` + `tronmcp onboard` 一键安装配置流程
- 将 `tronpy` 从核心依赖移至可选依赖（`full` extras），解决 Windows 编译问题
- 优化项目结构，分离 `cli.py` 和 `onboard.py` 职责

### Fixed
- 修复 `onboard.py` 轻量导入 `key_manager` 避免触发全量依赖链
- 优化虚拟环境路径检测，支持跨平台（Windows/Unix）
- 改进错误处理和用户提示信息

## [0.1.0] - 2025-02-08

### Added
- 初始版本发布
- 标准 MCP 工具：`tron_get_*`, `tron_build_tx`, `tron_sign_tx`, `tron_broadcast_tx`, `tron_transfer`
- 本地私钥管理（ECDSA secp256k1 + RFC 6979）
- TRONSCAN + TronGrid 客户端
- Gas 参数估算与安全审计
- 完整的测试套件

[Unreleased]: https://github.com/Neutralmilkzzz/MCPweb3/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Neutralmilkzzz/MCPweb3/releases/tag/v0.1.0
