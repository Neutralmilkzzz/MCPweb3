#!/usr/bin/env python3
"""
TRONMCP 一键安装脚本

用法:
    python install.py

功能:
    1. 创建虚拟环境
    2. 安装依赖
    3. 安装 tronmcp 命令
    4. 自动运行 onboard 配置向导
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def get_platform_info(install_dir):
    """获取当前平台信息"""
    system = platform.system()
    if system == "Windows":
        return {
            "name": "Windows",
            "activate_cmd": f'"{install_dir}\\.venv\\Scripts\\Activate.ps1"',
            "tronmcp_path": f'"{install_dir}\\.venv\\Scripts\\tronmcp.exe"',
            "shell": "powershell"
        }
    elif system == "Darwin":  # macOS
        return {
            "name": "macOS",
            "activate_cmd": f'source "{install_dir}/.venv/bin/activate"',
            "tronmcp_path": f'"{install_dir}/.venv/bin/tronmcp"',
            "shell": "bash"
        }
    else:  # Linux 或其他 Unix-like
        return {
            "name": "Linux",
            "activate_cmd": f'source "{install_dir}/.venv/bin/activate"',
            "tronmcp_path": f'"{install_dir}/.venv/bin/tronmcp"',
            "shell": "bash"
        }


def detect_python_command():
    """自动检测可用的 Python 命令"""
    # 尝试常见的 Python 命令
    python_commands = ['python', 'python3', 'py']
    
    for cmd in python_commands:
        try:
            # 检查命令是否存在
            result = subprocess.run(
                f'"{cmd}" --version',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return cmd
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    # 如果都没找到，返回默认的 python
    print("  ⚠️  未检测到 python/python3/py 命令，将使用 'python'")
    return 'python'


def run_command(cmd, description, capture_output=False):
    """运行命令并显示进度"""
    print(f"  ⏳ {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=capture_output,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            print(f"  ✅ {description}完成")
            return True
        else:
            print(f"  ❌ {description}失败: {result.stderr if capture_output else '返回码 ' + str(result.returncode)}")
            return False
    except subprocess.TimeoutExpired:
        print(f"  ❌ {description}超时")
        return False
    except Exception as e:
        print(f"  ❌ {description}异常: {e}")
        return False


def main():
    print("\n" + "="*60)
    print("  🐙 TRONMCP 一键安装")
    print("="*60 + "\n")

    # 显示 TRON logo
    logo = r"""
  ████████╗██████╗  ██████╗ ███╗   ██╗
  ╚══██╔══╝██╔══██╗██╔═══██╗████╗  ██║
     ██║   ██████╔╝██║   ██║██╔██╗ ██║
     ██║   ██╔══██╗██║   ██║██║╚██╗██║
     ██║   ██║  ██║╚██████╔╝██║ ╚████║
     ╚═╝   ╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
"""
    print(f"  {logo}")

    project_dir = Path(__file__).parent.resolve()
    venv_dir = project_dir / ".venv"
    
    # 确定安装目录（pyproject.toml 所在位置）
    mcp_server_dir = project_dir / "tron-mcp-server"
    if not (project_dir / "pyproject.toml").exists() and (mcp_server_dir / "pyproject.toml").exists():
        install_dir = mcp_server_dir
    else:
        install_dir = project_dir

    # Step 1: 检测 Python 命令
    print("📋 Step 1/4: 检测 Python 环境")
    python_cmd = detect_python_command()
    print(f"  ✅ 使用命令: {python_cmd}")
    
    # 获取 Python 版本
    try:
        result = subprocess.run(
            f'"{python_cmd}" --version',
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        python_version = result.stdout.strip() if result.stdout else result.stderr.strip()
        print(f"  ✅ {python_version}")
    except Exception as e:
        print(f"  ❌ 无法获取 Python 版本: {e}")
        sys.exit(1)
    
    # 检查 Python 版本是否 >= 3.10
    if sys.version_info < (3, 10):
        print("  ❌ 需要 Python 3.10 或更高版本")
        sys.exit(1)
    print()

    # Step 2: 创建虚拟环境
    print("📦 Step 2/4: 创建虚拟环境")
    if venv_dir.exists():
        print(f"  ⏳ 虚拟环境已存在，跳过创建")
    else:
        if not run_command(f'"{python_cmd}" -m venv "{venv_dir}"', "创建虚拟环境"):
            sys.exit(1)
    print()

    # Step 3: 安装依赖
    print("🔧 Step 3/4: 安装依赖包")
    
    # Windows 使用 python -m pip 避免文件锁定问题，Linux/macOS 可以直接使用 pip
    if platform.system() == "Windows":
        venv_python = f'"{venv_dir}/Scripts/python.exe"'
        pip_base_cmd = f'{venv_python} -m pip'
    else:
        pip_base_cmd = f'"{venv_dir}/bin/pip"'

    # 升级 pip
    if not run_command(f'{pip_base_cmd} install --upgrade pip', "升级 pip", capture_output=True):
        print("  ⚠️  pip 升级失败，继续安装...")

    # 安装项目（包含所有依赖）
    if not run_command(f'{pip_base_cmd} install -e "{install_dir}"', "安装 tron-mcp-server", capture_output=True):
        print("  ⚠️  安装失败，请检查错误信息")
        sys.exit(1)
    print()

    # Step 4: 完成
    print("🎉 Step 4/4: 安装完成！\n")
    print("="*60)
    print("  下一步：")
    print("="*60)
    print()
    
    # 获取平台信息
    platform_info = get_platform_info(install_dir)
    system = platform.system()
    
    print(f"  🖥️  检测到操作系统: {platform_info['name']}")
    print()
    print("  1️⃣  激活虚拟环境并运行配置向导：")
    print(f"     {platform_info['activate_cmd']}")
    print(f"     tronmcp onboard")
    print()
    print("  2️⃣  或者直接运行（无需激活）：")
    print(f"     {platform_info['tronmcp_path']} onboard")
    print()
    
    # 询问是否立即运行 onboard
    print("="*60)
    print()
    try:
        # 使用 questionary 如果可用，否则用 input
        try:
            import questionary
            run_now = questionary.select(
                "是否现在运行配置向导？",
                choices=[
                    "✅ 是的，立即配置",
                    "⏭️  跳过，稍后手动配置"
                ],
                default="✅ 是的，立即配置"
            ).ask()
        except ImportError:
            response = input("是否现在运行配置向导？(y/n): ").strip().lower()
            run_now = "yes" if response in ['y', 'yes', '是'] else "no"
        
        if run_now and ("是的" in run_now or run_now == "yes"):
            print("\n" + "="*60)
            print("  🚀 启动配置向导...")
            print("="*60 + "\n")
            
            # 使用虚拟环境的 Python 运行 onboard 模块
            if system == "Windows":
                venv_python = venv_dir / "Scripts" / "python.exe"
            else:
                venv_python = venv_dir / "bin" / "python"
            
            onboard_cmd = f'"{venv_python}" -m tron_mcp_server.onboard'
            if subprocess.run(onboard_cmd, shell=True).returncode != 0:
                print("  ⚠️  配置向导运行失败，请稍后手动运行：")
                print(f"     {platform_info['tronmcp_path']} onboard")
        else:
            print("\n  💡 稍后可以运行以下命令启动配置向导：")
            print(f"     {platform_info['tronmcp_path']} onboard")
            print()
    except KeyboardInterrupt:
        print("\n\n  👋 跳过配置向导")
    except Exception as e:
        print(f"\n  ⚠️  自动启动失败: {e}")
        print(f"     请手动运行: {platform_info['tronmcp_path']} onboard")
    
    print("\n" + "="*60)
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 安装已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 安装失败: {e}")
        sys.exit(1)
