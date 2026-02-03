import pytest

# 已知映射：TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t -> 0x41a614f803b6fd780986a42c78ec9c7f77e6ded13c
USDT_BASE58 = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"
USDT_HEX = "0x41a614f803b6fd780986a42c78ec9c7f77e6ded13c"
USDT_HEX_NOPREFIX = USDT_HEX[2:]


def test_get_balance_trx_converts_base58_to_hex(monkeypatch):
    from tron_mcp_server import tron_client

    captured = {}

    def fake_get(path, params=None):
        captured["path"] = path
        captured["params"] = params
        return {"balance": 0}

    monkeypatch.setattr(tron_client, "_get", fake_get)
    tron_client.get_balance_trx(USDT_BASE58)

    assert captured["path"] == "account"
    assert captured["params"]["address"] == USDT_BASE58


def test_get_usdt_balance_call_data_uses_hex_address(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(
        tron_client,
        "_get",
        lambda path, params=None: {
            "trc20token_balances": [
                {"tokenId": tron_client.USDT_CONTRACT_HEX, "balance": "1000000", "tokenDecimal": 6}
            ]
        },
    )
    balance = tron_client.get_usdt_balance(USDT_BASE58)
    assert balance == 1.0


def test_trc20_transfer_encoding_left_pad():
    from tron_mcp_server import tx_builder

    data = tx_builder._encode_transfer(USDT_HEX_NOPREFIX, 1)
    expected = "a9059cbb" + USDT_HEX_NOPREFIX.zfill(64) + hex(1)[2:].zfill(64)
    assert data == expected


def test_invalid_base58_address_is_rejected():
    from tron_mcp_server import validators

    # 长度过短
    assert not validators.is_valid_address("T12345")


def test_base58_invalid_chars_rejected():
    from tron_mcp_server import validators

    # Base58 不允许 0, O, I, l
    bad = "T0OIl" + "A" * 29
    assert not validators.is_valid_address(bad)


def test_build_tx_rejects_unknown_token():
    from tron_mcp_server import tx_builder

    with pytest.raises(ValueError):
        tx_builder.build_unsigned_tx("TFrom", "TTo", 1.0, token="ABC")


def test_build_tx_rejects_zero_amount():
    from tron_mcp_server import tx_builder

    with pytest.raises(ValueError):
        tx_builder.build_unsigned_tx("TFrom", "TTo", 0, token="TRX")


def test_txid_with_0x_prefix_is_accepted():
    from tron_mcp_server import validators

    assert validators.is_valid_txid("0x" + "a" * 64)


def test_txid_invalid_length_rejected():
    from tron_mcp_server import validators

    assert not validators.is_valid_txid("a" * 63)
    assert not validators.is_valid_txid("a" * 65)


def test_hex_address_must_start_with_41():
    from tron_mcp_server import validators

    # 0x42 开头不符合 TRON 地址规范
    assert not validators.is_valid_address("0x42" + "a" * 40)


def test_hex_address_length_strict():
    from tron_mcp_server import validators

    assert not validators.is_valid_address("0x41" + "a" * 39)
    assert not validators.is_valid_address("0x41" + "a" * 41)


def test_get_transaction_status_pending_receipt(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {})

    with pytest.raises(ValueError):
        tron_client.get_transaction_status("0x" + "a" * 64)


def test_get_transaction_status_missing_status(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(
        tron_client,
        "_get",
        lambda path, params=None: {"block": 16},
    )

    success, block_number = tron_client.get_transaction_status("0x" + "a" * 64)
    assert success is False
    assert block_number == 16


def test_get_gas_parameters_requires_result_key(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {})

    with pytest.raises(ValueError):
        tron_client.get_gas_parameters()


def test_get_network_status_requires_result_key(monkeypatch):
    from tron_mcp_server import tron_client

    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {})

    with pytest.raises(KeyError):
        tron_client.get_network_status()


def test_get_balance_trx_large_value_precision(monkeypatch):
    from tron_mcp_server import tron_client

    # very large int as string
    monkeypatch.setattr(tron_client, "_get", lambda path, params=None: {"balance": str(2**200)})

    balance = tron_client.get_balance_trx("0x41" + "a" * 40)
    assert balance > 0


def test_get_usdt_balance_large_value_precision(monkeypatch):
    from tron_mcp_server import tron_client

    # very large int as string
    monkeypatch.setattr(
        tron_client,
        "_get",
        lambda path, params=None: {
            "trc20token_balances": [
                {"tokenId": tron_client.USDT_CONTRACT_BASE58, "balance": str(2**160), "tokenDecimal": 6}
            ]
        },
    )

    balance = tron_client.get_usdt_balance("0x41" + "a" * 40)
    assert balance > 0


def test_build_tx_rejects_negative_amount():
    from tron_mcp_server import tx_builder

    with pytest.raises(ValueError):
        tx_builder.build_unsigned_tx("TFrom", "TTo", -0.01, token="TRX")


def test_build_tx_usdt_amount_rounding_edge(monkeypatch):
    from tron_mcp_server import tx_builder

    monkeypatch.setattr(tx_builder, "_get_ref_block", lambda: ("abcd", "ef12"))
    monkeypatch.setattr(tx_builder, "_timestamp_ms", lambda: 1700000000000)

    tx = tx_builder.build_unsigned_tx("F", "T", 0.000001, token="USDT")
    raw = tx["raw_data"]
    assert raw["contract"][0]["parameter"]["value"]["data"].endswith(hex(1)[2:].zfill(64))


def test_build_tx_trx_amount_rounding_edge(monkeypatch):
    from tron_mcp_server import tx_builder

    monkeypatch.setattr(tx_builder, "_get_ref_block", lambda: ("abcd", "ef12"))
    monkeypatch.setattr(tx_builder, "_timestamp_ms", lambda: 1700000000000)

    tx = tx_builder.build_unsigned_tx("F", "T", 0.000001, token="TRX")
    raw = tx["raw_data"]
    assert raw["contract"][0]["parameter"]["value"]["amount"] == 1
