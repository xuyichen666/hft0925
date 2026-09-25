# J:\NT_Course\config\APIConfig.py
import os


class APIConfig:
    # Read from env only — never commit real keys.
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "")

    BINANCE_TESTNET_API_KEY = os.getenv("BINANCE_TESTNET_API_KEY", "")
    BINANCE_TESTNET_API_SECRET = os.getenv("BINANCE_TESTNET_API_SECRET", "")

    # 交易对配置（永续合约）
    INSTRUMENTS = {
        "BTCUSDT-PERP.BINANCE": {
            "base_currency": "BTC",
            "quote_currency": "USDT",
            "price_precision": 2,
            "size_precision": 3,
        },
        "ETHUSDT-PERP.BINANCE": {
            "base_currency": "ETH",
            "quote_currency": "USDT",
            "price_precision": 2,
            "size_precision": 2,
        },
        "BNBUSDT-PERP.BINANCE": {
            "base_currency": "BNB",
            "quote_currency": "USDT",
            "price_precision": 2,
            "size_precision": 2,
        },
        "SOLUSDT-PERP.BINANCE": {
            "base_currency": "SOL",
            "quote_currency": "USDT",
            "price_precision": 3,
            "size_precision": 2,
        },
    }

    # 旧 U 本位测试网（课程钥匙）。空字符串会让 Nautilus 改打 demo-fapi.binance.com。
    BINANCE_TESTNET_HTTP = os.getenv("BINANCE_TESTNET_HTTP", "https://testnet.binancefuture.com")
    BINANCE_TESTNET_WS = os.getenv("BINANCE_TESTNET_WS", "")
