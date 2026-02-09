import asyncio
import os
import time
import httpx
from tron_mcp_server import formatters

os.chdir("../tron-mcp-server")

# 模拟配置
CONCURRENT_USERS = 50  # 模拟 50 个并发请求
TOTAL_REQUESTS = 200   # 总计发送 200 个测试任务

async def simulate_tx_query(client, task_id):
    """模拟一次复杂的交易查询与格式化流"""
    start_time = time.perf_counter()
    try:
        # 1. 模拟从 TRON 节点/API 获取的原始数据
        mock_raw_data = {
            "success": True,
            "block_number": 12345678,
            "token_type": "USDT",
            "amount": 100.5,
            "from_address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "to_address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "fee": 13500000,
            "timestamp": int(time.time() * 1000)
        }
        
        # 2. 调用你的格式化模块 (CPU 密集型操作测试)
        formatted = formatters.format_tx_status("tx_" + str(task_id), mock_raw_data)
        
        # 3. 模拟一次真实的异步网络请求 (可选，如果想测试 IO 性能)
        # await client.get("https://api.tronscan.org/api/system/status") 
        
        latency = time.perf_counter() - start_time
        return True, latency
    except Exception as e:
        return False, 0

async def main():
    print(f"🚀 开始压力测试: {CONCURRENT_USERS} 并发用户, 总计 {TOTAL_REQUESTS} 次请求")
    
    async with httpx.AsyncClient() as client:
        tasks = []
        for i in range(TOTAL_REQUESTS):
            tasks.append(simulate_tx_query(client, i))
        
        start_run = time.perf_counter()
        
        # 使用 semaphore 控制并发度
        sem = asyncio.Semaphore(CONCURRENT_USERS)
        async def sem_task(t):
            async with sem:
                return await t
        
        results = await asyncio.gather(*(sem_task(t) for t in tasks))
        
        total_time = time.perf_counter() - start_run
        
    # 统计结果
    successes = [r for r in results if r[0]]
    latencies = [r[1] for r in results if r[0]]
    
    print("\n" + "="*30)
    print(f"📊 测试报告")
    print(f"成功率: {len(successes)}/{TOTAL_REQUESTS} ({len(successes)/TOTAL_REQUESTS*100:.1f}%)")
    print(f"总耗时: {total_time:.2f} 秒")
    print(f"平均吞吐量 (TPS): {len(successes)/total_time:.2f} req/s")
    if latencies:
        print(f"平均响应延迟: {sum(latencies)/len(latencies)*1000:.2f} ms")
        print(f"最快响应: {min(latencies)*1000:.2f} ms")
        print(f"最慢响应: {max(latencies)*1000:.2f} ms")
    print("="*30)

if __name__ == "__main__":
    asyncio.run(main())
