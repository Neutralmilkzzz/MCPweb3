#!/usr/bin/env python3
import os

test_files = []
for root, dirs, files in os.walk('tests'):
    for f in files:
        if f.startswith('test_') or f == 'stress_test.py':
            test_files.append(os.path.join(root, f))

old_line = 'project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))'
new_line = 'project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))'

count = 0
for f in test_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            content = file.read()

        if old_line in content:
            new_content = content.replace(old_line, new_line)
            with open(f, 'w', encoding='utf-8') as file:
                file.write(new_content)
            count += 1
    except Exception as e:
        print(f'错误 {f}: {e}')

print(f'更新了 {count} 个文件')
