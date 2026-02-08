"""TRON AI Alipay — 交互式引导配置脚本

运行方式:
    tronmcp onboard        (安装后)
    python -m tron_mcp_server.onboard  (开发时)

功能:
    1. 选择网络（主网 mainnet / 测试网 nile）
    2. 引导用户配置 TRON_PRIVATE_KEY（隐密输入 + 即时派生地址校验）
    3. 引导配置 TRONGRID_API_KEY / TRONSCAN_API_KEY（含连接性测试）
    4. 持久化写入 .env 并设置安全权限
    5. 可选：直接启动 MCP 服务器
"""

import os
import sys
import time
import platform
from pathlib import Path

import httpx
import questionary
from questionary import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich import box

# 轻量导入：直接加载 key_manager，避免 __init__.py 触发全量依赖链
import importlib.util as _ilu

def _lazy_import_key_manager():
    """绕过 __init__.py 直接加载 key_manager 模块"""
    _spec = _ilu.find_spec("tron_mcp_server.key_manager")
    if _spec is None:
        # fallback: 通过相对路径加载
        _mod_path = Path(__file__).parent / "key_manager.py"
        _spec = _ilu.spec_from_file_location("tron_mcp_server.key_manager", _mod_path)
    assert _spec is not None, "无法找到 key_manager 模块"
    _mod = _ilu.module_from_spec(_spec)
    assert _spec.loader is not None, "模块 loader 为空"
    _spec.loader.exec_module(_mod)
    return _mod

_km = _lazy_import_key_manager()
get_address_from_private_key = _km.get_address_from_private_key

# ─────────────────────────────────────────────
# 全局样式
# ─────────────────────────────────────────────

console = Console()

# questionary 自定义主题 — 支付宝蓝
ALIPAY_STYLE = Style([
    ("qmark",       "fg:#1677FF bold"),       # 问号标记
    ("question",    "fg:#FFFFFF bold"),        # 问题文字
    ("answer",      "fg:#1677FF bold"),        # 用户回答
    ("pointer",     "fg:#1677FF bold"),        # 选择指针
    ("highlighted", "fg:#1677FF bold"),        # 高亮选项
    ("selected",    "fg:#1677FF"),             # 已选项
    ("instruction", "fg:#858585"),             # 提示说明
])

# 品牌色
BRAND_BLUE = "#1677FF"
BRAND_GREEN = "#52C41A"
BRAND_RED = "#FF4D4F"
BRAND_GOLD = "#FAAD14"
BRAND_CYAN = "#13C2C2"


# ─────────────────────────────────────────────
# 欢迎界面
# ─────────────────────────────────────────────

LOGO = r"""
  ████████╗██████╗  ██████╗ ███╗   ██╗
  ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
     ██║   ██████╔╝██║   ██║██╔██╗ ██║
     ██║   ██╔══██╗██║   ██║██║╚██╗██║
     ██║   ██║  ██║╚██████╔╝██║ ╚████║
     ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""


def show_welcome():
    """显示支付宝风格的欢迎面板"""
    logo_text = Text(LOGO, style=f"bold {BRAND_BLUE}")
    subtitle = Text.assemble(
        ("  🔗 TRON AI Alipay", f"bold {BRAND_BLUE}"),
        (" — ", "dim"),
        ("Web3 智能支付终端", f"bold {BRAND_CYAN}"),
    )
    tagline = Text("  让每一笔链上交易，像扫码支付一样简单\n", style="dim italic")

    content = Text()
    content.append_text(logo_text)
    content.append("\n")
    content.append_text(subtitle)
    content.append("\n")
    content.append_text(tagline)

    panel = Panel(
        Align.center(content),
        border_style=BRAND_BLUE,
        box=box.DOUBLE_EDGE,
        padding=(1, 4),
        title="[bold white]🐙 TRONMCP[/]",
        subtitle="[dim]v0.1.0 · Powered by MCP[/]",
    )
    console.print()
    console.print(panel)
    console.print()


# ─────────────────────────────────────────────
# Step 0: 网络选择
# ─────────────────────────────────────────────

def step_network() -> str | None:
    """引导用户选择 TRON 网络"""
    console.print(
        Panel(
            "[bold white]🌐 Step 1/6 · 网络选择[/]\n"
            "[dim]选择您要连接的 TRON 网络。主网用于真实交易，测试网用于开发调试。[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    network = questionary.select(
        "请选择 TRON 网络：",
        choices=[
            questionary.Choice("🟢 主网 (Mainnet)", value="mainnet"),
            questionary.Choice("🟡 Nile 测试网", value="nile"),
        ],
        style=ALIPAY_STYLE,
    ).ask()

    if network is None:
        return None

    if network == "mainnet":
        console.print(f"  [bold {BRAND_GREEN}]✅ 已选择主网[/] — 真实资产，请谨慎操作！")
    else:
        console.print(f"  [bold {BRAND_CYAN}]✅ 已选择 Nile 测试网[/] — 用于开发测试，无真实资产风险。")

    console.print()
    return network


# ─────────────────────────────────────────────
# Step 1: 私钥配置
# ─────────────────────────────────────────────

def step_private_key() -> str | None:
    """引导用户输入私钥并即时校验"""
    console.print(
        Panel(
            "[bold white]🔐 Step 2/6 · 私钥配置[/]\n"
            "[dim]您的私钥仅存储在本地 .env 文件中，绝不会上传到任何服务器。[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    for attempt in range(3):
        pk = questionary.password(
            "请输入您的 TRON 私钥（64 位十六进制）：",
            style=ALIPAY_STYLE,
        ).ask()

        if pk is None:
            # 用户按了 Ctrl+C
            return None

        pk = pk.strip()
        if pk.startswith(("0x", "0X")):
            pk = pk[2:]

        # 基础格式校验
        if len(pk) != 64:
            console.print(f"  [bold {BRAND_RED}]⚠️  私钥长度不正确[/]（期望 64 位，实际 {len(pk)} 位）")
            if attempt < 2:
                console.print(f"  [dim]还有 {2 - attempt} 次重试机会[/]\n")
            continue

        try:
            bytes.fromhex(pk)
        except ValueError:
            console.print(f"  [bold {BRAND_RED}]⚠️  私钥包含非法字符[/]，请确认为纯十六进制字符串。")
            if attempt < 2:
                console.print(f"  [dim]还有 {2 - attempt} 次重试机会[/]\n")
            continue

        # 派生地址
        try:
            address = get_address_from_private_key(pk)
        except Exception as e:
            console.print(f"  [bold {BRAND_RED}]❌ 私钥无法派生地址：{e}[/]")
            if attempt < 2:
                console.print(f"  [dim]还有 {2 - attempt} 次重试机会[/]\n")
            continue

        # 成功
        console.print()
        console.print(f"  [bold {BRAND_GREEN}]✅ 私钥校验通过[/]")
        console.print(
            f"  [bold {BRAND_GREEN}]✨ 欢迎回来！您的账户[/] "
            f"[bold white on {BRAND_BLUE}] {address} [/] "
            f"[bold {BRAND_GREEN}]已识别。[/]"
        )
        console.print()
        return pk

    console.print(f"\n  [bold {BRAND_RED}]❌ 三次输入均未通过校验，请确认私钥后重试。[/]\n")
    return None


# ─────────────────────────────────────────────
# Step 3: API Keys 配置
# ─────────────────────────────────────────────

def _test_trongrid_key(api_key: str, network: str = "mainnet") -> tuple[bool, str]:
    """
    向 TronGrid 发送轻量级请求以验证 API Key 有效性。
    返回 (是否成功, 消息)
    """
    # 根据网络选择 API URL
    base_url = "https://api.trongrid.io" if network == "mainnet" else "https://nile.trongrid.io"
    url = f"{base_url}/wallet/getnowblock"
    headers = {"TRON-PRO-API-KEY": api_key} if api_key else {}
    try:
        resp = httpx.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            block_num = data.get("block_header", {}).get("raw_data", {}).get("number", "N/A")
            return True, f"当前区块高度: #{block_num}"
        else:
            return False, f"HTTP {resp.status_code}: {resp.text[:120]}"
    except httpx.TimeoutException:
        return False, "请求超时，请检查网络连接"
    except Exception as e:
        return False, str(e)


def step_api_keys(network: str) -> tuple[str, str] | None:
    """引导用户输入 API Keys 并进行连接性测试"""
    console.print(
        Panel(
            "[bold white]🔑 Step 3/6 · API Keys 配置[/]\n"
            "[dim]TronGrid API Key 用于链上数据查询，TronScan API Key 用于浏览器数据。\n"
            "免费申请: https://www.trongrid.io/  |  https://tronscan.org/[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    # ── TronGrid API Key ──
    trongrid_key = questionary.text(
        "请输入 TronGrid API Key：",
        style=ALIPAY_STYLE,
        instruction="(直接回车可跳过，使用公共限速接口)",
    ).ask()

    if trongrid_key is None:
        return None

    trongrid_key = trongrid_key.strip()

    # 连接性测试
    if trongrid_key:
        console.print(f"  [dim]🔄 正在验证 TronGrid API Key ({network})...[/]", end="")
        ok, msg = _test_trongrid_key(trongrid_key, network)
        if ok:
            console.print(f"\r  [bold {BRAND_GREEN}]✅ TronGrid 连接成功[/] — {msg}       ")
        else:
            console.print(f"\r  [bold {BRAND_GOLD}]⚠️  TronGrid 连接异常[/] — {msg}       ")
            proceed = questionary.confirm(
                "API Key 验证未通过，是否仍然保存？",
                default=False,
                style=ALIPAY_STYLE,
            ).ask()
            if proceed is None:
                return None
            if not proceed:
                trongrid_key = ""
                console.print(f"  [dim]已跳过 TronGrid API Key[/]")
    else:
        console.print(f"  [dim]⏭️  已跳过 TronGrid API Key，将使用公共限速接口[/]")

    console.print()

    # ── TronScan API Key ──
    tronscan_key = questionary.text(
        "请输入 TronScan API Key：",
        style=ALIPAY_STYLE,
        instruction="(直接回车可跳过)",
    ).ask()

    if tronscan_key is None:
        return None

    tronscan_key = tronscan_key.strip()

    if tronscan_key:
        console.print(f"  [bold {BRAND_GREEN}]✅ TronScan API Key 已记录[/]")
    else:
        console.print(f"  [dim]⏭️  已跳过 TronScan API Key[/]")

    console.print()
    return trongrid_key, tronscan_key


# ─────────────────────────────────────────────
# Step 4: 持久化 .env
# ─────────────────────────────────────────────

def step_save_env(network: str, private_key: str, trongrid_key: str, tronscan_key: str) -> bool:
    """将配置写入 .env 文件并设置安全权限"""
    console.print(
        Panel(
            "[bold white]💾 Step 4/6 · 保存配置[/]\n"
            "[dim]配置将写入项目根目录的 .env 文件，并设置仅当前用户可读写。[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    env_path = Path.cwd() / ".env"

    # 读取已有 .env 内容（保留用户自定义项）
    existing_lines: list[str] = []
    existing_keys: set[str] = set()
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    key = stripped.split("=", 1)[0].strip()
                    # 跳过即将覆盖的 key
                    if key in ("TRON_NETWORK", "TRON_PRIVATE_KEY", "TRONGRID_API_KEY", "TRONSCAN_API_KEY"):
                        existing_keys.add(key)
                        continue
                existing_lines.append(line.rstrip("\n"))

    # 构建新内容
    new_entries = []
    if existing_keys:
        console.print(f"  [bold {BRAND_GOLD}]⚠️  检测到已有配置，将覆盖以下项：[/] {', '.join(sorted(existing_keys))}")

    new_entries.append("")
    new_entries.append("# ═══════════════════════════════════════════")
    new_entries.append("# 🏦 TRON AI Alipay — 自动生成配置")
    new_entries.append("# ═══════════════════════════════════════════")
    new_entries.append("")
    new_entries.append(f"TRON_NETWORK={network}")
    new_entries.append(f"TRON_PRIVATE_KEY={private_key}")
    if trongrid_key:
        new_entries.append(f"TRONGRID_API_KEY={trongrid_key}")
    if tronscan_key:
        new_entries.append(f"TRONSCAN_API_KEY={tronscan_key}")
    new_entries.append("")

    final_content = "\n".join(existing_lines + new_entries) + "\n"

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        console.print(f"  [bold {BRAND_GREEN}]✅ 配置已写入[/] {env_path}")
    except Exception as e:
        console.print(f"  [bold {BRAND_RED}]❌ 写入失败：{e}[/]")
        return False

    # 设置文件权限 (仅 Unix/macOS)
    if platform.system() != "Windows":
        try:
            os.chmod(str(env_path), 0o600)
            console.print(f"  [bold {BRAND_GREEN}]🔒 文件权限已设置为 600[/]（仅当前用户可读写）")
        except Exception as e:
            console.print(f"  [bold {BRAND_GOLD}]⚠️  权限设置失败：{e}[/]（请手动执行 chmod 600 .env）")
    else:
        console.print(f"  [dim]💡 Windows 系统请确保 .env 文件不被意外共享[/]")

    console.print()
    return True


# ─────────────────────────────────────────────
# 完成摘要
# ─────────────────────────────────────────────

def show_summary(network: str, private_key: str, trongrid_key: str, tronscan_key: str):
    """显示配置完成的摘要表格"""
    address = get_address_from_private_key(private_key)

    table = Table(
        title="🏦 配置摘要",
        box=box.ROUNDED,
        border_style=BRAND_BLUE,
        title_style=f"bold {BRAND_BLUE}",
        show_lines=True,
        padding=(0, 2),
    )
    table.add_column("配置项", style="bold white", min_width=20)
    table.add_column("状态", min_width=40)

    # 网络状态
    network_display = f"[bold {BRAND_GREEN}]主网 Mainnet[/]" if network == "mainnet" else f"[bold {BRAND_CYAN}]Nile 测试网[/]"
    table.add_row("🌐 网络", network_display)
    # 私钥（脱敏显示）
    masked_pk = private_key[:6] + "••••••••" + private_key[-4:]
    table.add_row("🔐 私钥", f"[dim]{masked_pk}[/]")
    table.add_row("📍 钱包地址", f"[bold {BRAND_CYAN}]{address}[/]")
    table.add_row(
        "🌐 TronGrid Key",
        f"[bold {BRAND_GREEN}]已配置[/]" if trongrid_key else f"[dim]未配置（公共接口）[/]",
    )
    table.add_row(
        "🔍 TronScan Key",
        f"[bold {BRAND_GREEN}]已配置[/]" if tronscan_key else f"[dim]未配置[/]",
    )
    table.add_row("📁 配置文件", f"[dim]{Path.cwd() / '.env'}[/]")

    console.print(table)
    console.print()


# ─────────────────────────────────────────────
# Step 5: 环境变量配置（可选）
# ─────────────────────────────────────────────

def step_setup_path() -> bool:
    """
    询问用户是否将虚拟环境 bin/Scripts 目录添加到 PATH，
    以便在任何位置使用 tronmcp 命令。
    """
    console.print(
        Panel(
            "[bold white]⚙️  环境变量配置[/]\n"
            "[dim]是否将虚拟环境的可执行文件目录添加到系统 PATH？\n"
            "添加后，您可以在任意目录直接使用 'tronmcp' 命令。[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    choice = questionary.confirm(
        "是否自动添加到 PATH？",
        default=True,
        style=ALIPAY_STYLE,
    ).ask()

    if choice is None:
        return False

    if not choice:
        console.print(f"  [dim]⏭️  已跳过 PATH 配置[/]")
        return True

    # 根据操作系统确定虚拟环境的可执行文件目录
    system = platform.system()
    if system == "Windows":
        venv_subdir = "Scripts"
    else:
        venv_subdir = "bin"

    venv_path = Path(__file__).parent.parent.parent / ".venv" / venv_subdir
    if not venv_path.exists():
        console.print(f"  [bold {BRAND_GOLD}]⚠️  未找到虚拟环境目录: {venv_path}[/]")
        console.print(f"  [dim]请手动将虚拟环境的 {venv_subdir} 目录添加到 PATH。[/]")
        return True

    # Windows: 使用 setx 添加到用户 PATH
    if system == "Windows":
        try:
            import subprocess
            # 获取当前用户 PATH
            result = subprocess.run(
                ["setx", "PATH", f"%PATH%;{venv_path}"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                console.print(f"  [bold {BRAND_GREEN}]✅ 已将虚拟环境添加到 PATH[/]")
                console.print(f"  [dim]路径: {venv_path}[/]")
                console.print(f"  [dim]注意：需要重启终端或重新登录才能生效。[/]")
            else:
                console.print(f"  [bold {BRAND_RED}]❌ 添加失败: {result.stderr}[/]")
                console.print(f"  [dim]请手动将以下目录添加到 PATH:[/]")
                console.print(f"  [bold]{venv_path}[/]")
        except Exception as e:
            console.print(f"  [bold {BRAND_RED}]❌ 添加失败: {e}[/]")
            console.print(f"  [dim]请手动将以下目录添加到 PATH:[/]")
            console.print(f"  [bold]{venv_path}[/]")
    else:
        # Unix/macOS/Linux: 建议手动添加
        console.print(f"  [bold {BRAND_GOLD}]ℹ️  请手动将以下目录添加到 PATH:[/]")
        console.print(f"  [bold]{venv_path}[/]")
        console.print(f"  [dim]例如，在 ~/.bashrc 或 ~/.zshrc 中添加:[/]")
        console.print(f"  [dim]export PATH=\"$PATH:{venv_path}\"[/]")

    return True


# ─────────────────────────────────────────────
# Step 6: 启动服务器
# ─────────────────────────────────────────────

def _find_server_process(port: int = 8765) -> list[dict]:
    """
    查找占用端口的 MCP 服务器进程。
    返回进程信息列表 [{pid, name, port}]
    """
    try:
        import subprocess
        system = platform.system()
        pids = set()

        if system == "Windows":
            # Windows: 使用 netstat 和 findstr
            result = subprocess.run(
                ["netstat", "-ano", "|", "findstr", f":{port}"],
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            lines = result.stdout.strip().split("\n") if result.stdout else []
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and parts[3].startswith("LISTENING"):
                    pids.add(parts[4])
        else:
            # Unix/Linux/macOS: 使用 lsof 或 ss
            try:
                # 优先使用 lsof
                result = subprocess.run(
                    ["lsof", "-i", f":{port}", "-t"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    pids.update(result.stdout.strip().split("\n"))
                else:
                    # 尝试使用 ss
                    result = subprocess.run(
                        ["ss", "-ltnp", "|", "grep", f":{port}"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )
                    lines = result.stdout.strip().split("\n") if result.stdout else []
                    for line in lines:
                        if "tron" in line.lower():
                            parts = line.split()
                            for part in parts:
                                if part.isdigit():
                                    pids.add(part)
                                    break
            except Exception:
                pass

        processes = []
        for pid in pids:
            pid = pid.strip()
            if not pid:
                continue
            try:
                if system == "Windows":
                    # Windows: 使用 tasklist
                    ps = subprocess.run(
                        ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV"],
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if ps.returncode == 0 and "tron" in ps.stdout.lower():
                        processes.append({"pid": pid, "name": "tron-mcp-server", "port": port})
                else:
                    # Unix/Linux/macOS: 使用 ps
                    ps = subprocess.run(
                        ["ps", "-p", pid, "-o", "comm="],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if ps.returncode == 0 and "tron" in ps.stdout.lower():
                        processes.append({"pid": pid, "name": "tron-mcp-server", "port": port})
            except Exception:
                continue
        return processes
    except Exception as e:
        console.print(f"  [dim]⚠️  进程检测失败: {e}[/]")
        return []


def _kill_process(pid: str) -> bool:
    """强制终止指定 PID 的进程"""
    try:
        import subprocess
        system = platform.system()

        if system == "Windows":
            result = subprocess.run(
                ["taskkill", "/F", "/PID", pid],
                shell=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            # Unix/Linux/macOS: 使用 kill -9
            result = subprocess.run(
                ["kill", "-9", pid],
                capture_output=True,
                text=True,
                timeout=10,
            )

        return result.returncode == 0
    except Exception as e:
        console.print(f"  [bold {BRAND_RED}]❌ 终止进程失败: {e}[/]")
        return False


def step_start_server() -> bool:
    """询问用户是否立即启动 MCP 服务器（含重启检测）"""
    console.print(
        Panel(
            "[bold white]🚀 Step 6/6 · 启动服务器[/]\n"
            "[dim]配置已完成！是否立即启动 MCP 服务器？\n"
            "启动后，您可以通过 AI Agent（如 Claude）连接并使用 TRON 功能。[/]",
            border_style=BRAND_BLUE,
            box=box.ROUNDED,
        )
    )

    choice = questionary.select(
        "请选择启动模式：",
        choices=[
            questionary.Choice("🖥️  Stdio 模式（默认，用于 Claude Desktop）", value="stdio"),
            questionary.Choice("🌐 SSE 模式（HTTP 服务，用于远程连接）", value="sse"),
            questionary.Choice("⏭️  暂不启动，稍后手动运行", value="skip"),
        ],
        style=ALIPAY_STYLE,
    ).ask()

    if choice is None:
        return False

    if choice == "skip":
        console.print()
        console.print(
            Panel(
                "[bold white]✨ 配置完成！[/]\n\n"
                "稍后您可以通过以下命令启动服务器：\n\n"
                f"  [bold]tron-mcp-server[/]          # Stdio 模式\n"
                f"  [bold]tron-mcp-server --sse[/]    # SSE 模式\n\n"
                "[dim]祝您使用愉快！ 🎉[/]",
                border_style=BRAND_GREEN,
                box=box.ROUNDED,
            )
        )
        return True

    # ── 检测并处理已有进程 ──
    port = 8765
    if choice == "sse":
        port = int(os.getenv("MCP_PORT", "8765"))

    existing = _find_server_process(port)
    if existing:
        console.print(f"\n  [bold {BRAND_GOLD}]⚠️  检测到已有 MCP 服务器进程在运行：[/]")
        for p in existing:
            console.print(f"    PID: {p['pid']}  |  {p['name']}  |  端口: {p['port']}")
        console.print()

        action = questionary.select(
            "请选择操作：",
            choices=[
                questionary.Choice("🔄 自动重启（停止旧进程并启动新进程）", value="restart"),
                questionary.Choice("❌ 取消启动", value="cancel"),
            ],
            style=ALIPAY_STYLE,
        ).ask()

        if action == "cancel" or action is None:
            console.print(f"\n  [bold {BRAND_GOLD}]👋 已取消启动。[/]\n")
            return True

        # 停止旧进程
        console.print(f"  [dim]🛑 正在停止旧进程...[/]")
        for p in existing:
            if _kill_process(p["pid"]):
                console.print(f"  [bold {BRAND_GREEN}]✅ 已终止 PID {p['pid']}[/]")
            else:
                console.print(f"  [bold {BRAND_RED}]❌ 无法终止 PID {p['pid']}[/]")
        console.print()

    # ── 启动服务器 ──
    console.print()
    console.print(f"  [bold {BRAND_GREEN}]🚀 正在启动 MCP 服务器 ({choice} 模式，端口 {port})...[/]")
    console.print(f"  [dim]按 Ctrl+C 可停止服务器[/]")
    console.print()

    try:
        import subprocess
        # 根据操作系统确定虚拟环境的 Python 路径
        system = platform.system()
        if system == "Windows":
            venv_python = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
        else:
            venv_python = Path(__file__).parent.parent.parent / ".venv" / "bin" / "python"

        if not venv_python.exists():
            console.print(f"  [bold {BRAND_GOLD}]⚠️  未找到虚拟环境 Python: {venv_python}[/]")
            console.print(f"  [dim]请先运行 install.py 安装依赖。[/]")
            return True

        cmd = [str(venv_python), "-m", "tron_mcp_server.server"]
        if choice == "sse":
            cmd.append("--sse")

        console.print(f"  [dim]命令: {' '.join(cmd)}[/]\n")

        # 使用 subprocess 运行服务器
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print(f"\n  [bold {BRAND_GOLD}]👋 服务器已停止。[/]\n")
    except Exception as e:
        console.print(f"\n  [bold {BRAND_RED}]❌ 启动失败：{e}[/]")
        console.print(f"  [dim]请尝试手动运行: {venv_python} -m tron_mcp_server.server[/]\n")

    return True


# ─────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────

def main():
    """onboard 主入口"""
    try:
        show_welcome()

        # ── Step 1: 网络选择 ──
        network = step_network()
        if not network:
            console.print(f"\n  [bold {BRAND_GOLD}]👋 配置已取消，期待下次再见！[/]\n")
            sys.exit(0)

        # ── Step 2: 私钥 ──
        private_key = step_private_key()
        if not private_key:
            console.print(f"\n  [bold {BRAND_GOLD}]👋 配置已取消，期待下次再见！[/]\n")
            sys.exit(0)

        # ── Step 3: API Keys ──
        result = step_api_keys(network)
        if result is None:
            console.print(f"\n  [bold {BRAND_GOLD}]👋 配置已取消，期待下次再见！[/]\n")
            sys.exit(0)
        trongrid_key, tronscan_key = result

        # ── Step 4: 保存 ──
        success = step_save_env(network, private_key, trongrid_key, tronscan_key)
        if not success:
            console.print(f"\n  [bold {BRAND_RED}]❌ 配置保存失败，请检查文件权限后重试。[/]\n")
            sys.exit(1)

        # ── 完成 ──
        show_summary(network, private_key, trongrid_key, tronscan_key)

        # ── Step 5: 环境变量配置 ──
        step_setup_path()

        # ── Step 6: 启动服务器 ──
        step_start_server()

    except KeyboardInterrupt:
        console.print(f"\n\n  [bold {BRAND_GOLD}]👋 操作已中断，您的数据未被保存。再见！[/]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n  [bold {BRAND_RED}]💥 发生意外错误：{e}[/]")
        console.print(f"  [dim]如需帮助，请提交 Issue 至项目仓库。[/]\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
