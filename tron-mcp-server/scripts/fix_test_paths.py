#!/usr/bin/env python3
"""修复测试文件的路径设置"""

import os

# 需要更新的文件列表
files = [
    'tests/unit/test_validators.py',
    'tests/unit/test_formatters.py',
    'tests/unit/test_key_manager.py',
    'tests/integration/test_trongrid_client.py',
    'tests/integration/test_tron_client.py',
    'tests/integration/test_tx_builder_new.py',
    'tests/integration/test_tx_builder_integration.py',
    'tests/integration/test_transfer_flow.py',
    'tests/integration/test_call_router_actions.py',
    'tests/integration/test_call_router_queries.py',
    'tests/functional/test_account_tokens.py',
    'tests/functional/test_account_resources.py',
    'tests/functional/test_address_book.py',
    'tests/functional/test_config_and_skills.py',
    'tests/functional/test_internal_transactions.py',
    'tests/functional/test_memo_functionality.py',
    'tests/functional/test_qrcode.py',
    'tests/functional/test_server_tools.py',
    'tests/functional/test_sign_broadcast.py',
    'tests/functional/test_sign_tx.py',
    'tests/functional/test_transaction_history.py',
    'tests/regression/test_balance_bug_fix.py',
    'tests/regression/test_known_issues.py',
    'tests/stress/stress_test.py'
]

old_line = 'project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))'
new_line = 'project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))'

for f in files:
    if os.path.exists(f):
        # 尝试不同编码读取
        for encoding in ['utf-8-sig', 'utf-8', 'latin-1', 'cp1252']:
            try:
                with open(f, 'r', encoding=encoding) as file:
                    content = file.read()
                break
            except UnicodeDecodeError:
                continue
        else:
            print(f"警告: 无法读取 {f}, 跳过")
            continue

        if old_line in content:
            new_content = content.replace(old_line, new_line)
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            print(f'✓ 已更新: {f}')
        else:
            print(f'✗ 未找到目标行: {f}')
    else:
        print(f'✗ 文件不存在: {f}')

print('\n完成！')
