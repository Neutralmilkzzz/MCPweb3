#!/usr/bin/env python3
"""运行测试套件并生成报告"""

import sys
import os
import unittest

# 确保项目目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == '__main__':
    # 导入测试模块
    from test_known_issues import *
    
    # 加载所有测试
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules['test_known_issues'])
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    print('\n' + '='*60)
    print('=== 测试总结 ===')
    print(f'总测试数: {result.testsRun}')
    print(f'成功: {result.testsRun - len(result.failures) - len(result.errors)}')
    print(f'失败: {len(result.failures)}')
    print(f'错误: {len(result.errors)}')
    print('='*60)
    
    # 退出码
    sys.exit(0 if result.wasSuccessful() else 1)