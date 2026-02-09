"""测试交易历史查询功能"""

import pytest
from unittest.mock import patch, MagicMock
from tron_mcp_server import call_router, tron_client, formatters

os.chdir("../tron-mcp-server")

class TestGetTransactionHistory:
    """测试 get_transaction_history 功能"""

    def test_missing_address_returns_error(self):
        """缺少 address 参数应返回错误"""
        result = call_router.call("get_transaction_history", {})
        assert "error" in result
        assert "address" in result.get("summary", "").lower()

    def test_invalid_address_returns_error(self):
        """无效地址格式应返回错误"""
        result = call_router.call("get_transaction_history", {
            "address": "invalid_address_123"
        })
        assert "error" in result
        assert "invalid" in result.get("summary", "").lower()

    def test_limit_validation(self):
        """limit 参数应被限制在 1-50 范围内"""
        # 测试超过最大值应返回错误
        result = call_router.call("get_transaction_history", {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "limit": 100
        })
        assert "error" in result
        assert "1-50" in result.get("summary", "")
        
        # 测试小于最小值应返回错误
        result = call_router.call("get_transaction_history", {
            "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
            "limit": 0
        })
        assert "error" in result
        
        # 测试有效值应成功
        with patch('tron_mcp_server.tron_client.get_transfer_history') as mock_trx, \
             patch('tron_mcp_server.tron_client.get_trc20_transfer_history') as mock_trc20:
            
            mock_trx.return_value = {"data": [], "total": 0}
            mock_trc20.return_value = {"token_transfers": [], "total": 0}
            
            result = call_router.call("get_transaction_history", {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "limit": 20
            })
            assert "error" not in result

    def test_query_all_tokens(self):
        """token=None 时应合并 TRX 和 TRC20 交易"""
        with patch('tron_mcp_server.tron_client.get_transfer_history') as mock_trx, \
             patch('tron_mcp_server.tron_client.get_trc20_transfer_history') as mock_trc20:
            
            # 模拟 TRX 转账数据
            mock_trx.return_value = {
                "data": [
                    {
                        "transactionHash": "trx_tx_1",
                        "transferFromAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                        "transferToAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                        "amount": 1000000,
                        "tokenName": "_",
                        "timestamp": 1640000000000
                    }
                ],
                "total": 1
            }
            
            # 模拟 TRC20 转账数据
            mock_trc20.return_value = {
                "token_transfers": [
                    {
                        "transaction_id": "trc20_tx_1",
                        "from_address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                        "to_address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                        "quant": "1000000",
                        "tokenInfo": {
                            "tokenAbbr": "USDT",
                            "tokenDecimal": 6
                        },
                        "block_ts": 1640000001000
                    }
                ],
                "total": 1
            }
            
            result = call_router.call("get_transaction_history", {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "limit": 10
            })
            
            # 验证两个 API 都被调用
            assert mock_trx.called
            assert mock_trc20.called
            
            # 验证结果包含合并的交易
            assert result["total"] == 2
            assert len(result["transfers"]) == 2

    def test_query_trx_only(self):
        """token="TRX" 时应只查询 TRX 转账"""
        with patch('tron_mcp_server.tron_client.get_transfer_history') as mock_trx:
            mock_trx.return_value = {
                "data": [
                    {
                        "transactionHash": "trx_tx_1",
                        "transferFromAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                        "transferToAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                        "amount": 1000000,
                        "tokenName": "_",
                        "timestamp": 1640000000000
                    }
                ],
                "total": 1
            }
            
            result = call_router.call("get_transaction_history", {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "token": "TRX"
            })
            
            # 验证调用时使用了 token="_"
            assert mock_trx.called
            assert mock_trx.call_args[1]["token"] == "_"
            assert result["token_filter"] == "TRX"

    def test_query_usdt_only(self):
        """token="USDT" 时应只查询 USDT (TRC20) 转账"""
        with patch('tron_mcp_server.tron_client.get_trc20_transfer_history') as mock_trc20:
            mock_trc20.return_value = {
                "token_transfers": [
                    {
                        "transaction_id": "usdt_tx_1",
                        "from_address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                        "to_address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                        "quant": "1000000",
                        "tokenInfo": {
                            "tokenAbbr": "USDT",
                            "tokenDecimal": 6
                        },
                        "block_ts": 1640000000000
                    }
                ],
                "total": 1
            }
            
            result = call_router.call("get_transaction_history", {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "token": "USDT"
            })
            
            # 验证调用时使用了 USDT 合约地址
            assert mock_trc20.called
            assert mock_trc20.call_args[1]["contract_address"] == tron_client.USDT_CONTRACT_BASE58
            assert result["token_filter"] == "USDT"

    def test_query_trc20_contract_address(self):
        """token 为 TRC20 合约地址时应查询该代币的转账"""
        contract_addr = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
        
        with patch('tron_mcp_server.tron_client.get_trc20_transfer_history') as mock_trc20:
            mock_trc20.return_value = {
                "token_transfers": [],
                "total": 0
            }
            
            result = call_router.call("get_transaction_history", {
                "address": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "token": contract_addr
            })
            
            # 验证调用时使用了指定的合约地址
            assert mock_trc20.called
            assert mock_trc20.call_args[1]["contract_address"] == contract_addr


class TestFormatTransactionHistory:
    """测试 format_transaction_history 函数"""

    def test_format_basic_transaction(self):
        """测试基本交易格式化"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        transfers = [
            {
                "transactionHash": "abc123",
                "transferFromAddress": "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7",
                "transferToAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
                "amount": 1000000,
                "tokenName": "_",
                "timestamp": 1640000000000
            }
        ]
        
        result = formatters.format_transaction_history(address, transfers, 1)
        
        assert result["address"] == address
        assert result["total"] == 1
        assert result["displayed"] == 1
        assert len(result["transfers"]) == 1
        
        tx = result["transfers"][0]
        assert tx["txid"] == "abc123"
        assert tx["from"] == "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        assert tx["to"] == "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf"
        assert tx["amount"] == 1.0  # 1000000 / 10^6
        assert tx["token"] == "TRX"  # "_" 转换为 "TRX"
        assert tx["direction"] == "OUT"  # from == address

    def test_direction_detection(self):
        """测试方向检测逻辑"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        
        # 测试 OUT 方向
        transfers_out = [{
            "transactionHash": "tx1",
            "transferFromAddress": address,
            "transferToAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "amount": 1000000,
            "tokenName": "_",
            "timestamp": 1640000000000
        }]
        result = formatters.format_transaction_history(address, transfers_out, 1)
        assert result["transfers"][0]["direction"] == "OUT"
        
        # 测试 IN 方向
        transfers_in = [{
            "transactionHash": "tx2",
            "transferFromAddress": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "transferToAddress": address,
            "amount": 1000000,
            "tokenName": "_",
            "timestamp": 1640000000000
        }]
        result = formatters.format_transaction_history(address, transfers_in, 1)
        assert result["transfers"][0]["direction"] == "IN"
        
        # 测试 SELF 方向
        transfers_self = [{
            "transactionHash": "tx3",
            "transferFromAddress": address,
            "transferToAddress": address,
            "amount": 1000000,
            "tokenName": "_",
            "timestamp": 1640000000000
        }]
        result = formatters.format_transaction_history(address, transfers_self, 1)
        assert result["transfers"][0]["direction"] == "SELF"

    def test_trc20_token_info_parsing(self):
        """测试 TRC20 代币信息解析"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        transfers = [{
            "transaction_id": "usdt_tx",
            "from_address": address,
            "to_address": "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf",
            "quant": "1000000",
            "tokenInfo": {
                "tokenAbbr": "USDT",
                "tokenDecimal": 6
            },
            "block_ts": 1640000000000
        }]
        
        result = formatters.format_transaction_history(address, transfers, 1)
        
        tx = result["transfers"][0]
        assert tx["txid"] == "usdt_tx"
        assert tx["token"] == "USDT"
        assert tx["amount"] == 1.0  # 1000000 / 10^6

    def test_summary_includes_filter(self):
        """测试摘要包含筛选条件"""
        address = "TLa2f6VPqDgRE67v1736s7bJ8Ray5wYjU7"
        
        # 无筛选
        result = formatters.format_transaction_history(address, [], 10)
        assert "筛选条件" not in result["summary"]
        
        # 有筛选
        result = formatters.format_transaction_history(address, [], 10, token_filter="USDT")
        assert "筛选条件：USDT" in result["summary"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
