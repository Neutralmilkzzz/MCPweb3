import pytest


@pytest.fixture
def client(monkeypatch):
    from tron_mcp_server import tron_client

    # Stub the http call
    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: (path, params))
    return tron_client


def test_get_usdt_balance_parses_hex(monkeypatch):
    from tron_mcp_server import tron_client

    # Mock TRONSCAN response
    monkeypatch.setattr(
        tron_client,
        "_get",
        lambda path, params=None: {
            "trc20token_balances": [
                {
                    "tokenId": tron_client.USDT_CONTRACT_BASE58,
                    "balance": "125000000",
                    "tokenDecimal": 6,
                }
            ]
        },
    )
    balance = tron_client.get_usdt_balance("TXYZ")
    # 125000000 / 1e6 = 125.0 USDT
    assert balance == 125.0


def test_get_balance_trx_parses_hex(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {"balance": 1_000_000})
    balance = tron_client.get_balance_trx("TXYZ")
    assert balance == pytest.approx(1.0)


def test_get_gas_parameters(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(
        tron_client,
        "_get",
        lambda path, params=None: {
            "chainParameter": [{"key": "getEnergyFee", "value": 420}]
        },
    )
    gas = tron_client.get_gas_parameters()
    assert gas == 420


def test_get_transaction_status_success(monkeypatch):
    from tron_mcp_server import tron_client

    api_response = {"contractRet": "SUCCESS", "block": 16}
    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: api_response)

    status, block_number = tron_client.get_transaction_status("0xabc")
    assert status is True
    assert block_number == 16


def test_get_transaction_status_failure(monkeypatch):
    from tron_mcp_server import tron_client

    api_response = {"contractRet": "OUT_OF_ENERGY", "block": 16}
    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: api_response)

    status, block_number = tron_client.get_transaction_status("0xabc")
    assert status is False
    assert block_number == 16


def test_get_network_status(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(
        tron_client, "_get", lambda path, params=None: {"data": [{"number": 0x123}]}
    )

    block_number = tron_client.get_network_status()
    assert block_number == 0x123


def test_post_called_with_correct_method_for_balance(monkeypatch):
    """测试 get_balance_trx 调用正确的 API 路径"""
    from tron_mcp_server import tron_client

    captured = {}

    def fake_get(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"balance": 0}

    monkeypatch.setattr(tron_client, "_get", fake_get)
    tron_client.get_balance_trx("TXYZ")

    assert captured["path"] == "account"
    assert captured["params"]["address"] == "TXYZ"


def test_post_called_with_correct_method_for_usdt(monkeypatch):
    """测试 get_usdt_balance 调用正确的 API 路径"""
    from tron_mcp_server import tron_client

    captured = {}

    def fake_get(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"trc20token_balances": []}

    monkeypatch.setattr(tron_client, "_get", fake_get)
    tron_client.get_usdt_balance("TXYZ")

    assert captured["path"] == "account"
    assert captured["params"]["address"] == "TXYZ"


def test_post_raises_on_no_result(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {})

    with pytest.raises(ValueError):
        tron_client.get_gas_parameters()
