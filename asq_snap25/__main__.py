from asq_snap25.live import build_node
import os

if __name__ == "__main__":
    testnet = os.getenv("BINANCE_TESTNET", "1") != "0"
    node = build_node(testnet=testnet)
    try:
        node.run()
    finally:
        node.dispose()
