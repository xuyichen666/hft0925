import requests
import socket


def test_connection():
    print("测试币安 USDT-M 合约连通性（公开时间接口，不带密钥）...")
    hosts = [
        ("主网", "https://fapi.binance.com"),
        ("Demo/Nautilus TESTNET", "https://demo-fapi.binance.com"),
        ("旧期货测试网", "https://testnet.binancefuture.com"),
    ]
    try:
        ip = socket.gethostbyname("fapi.binance.com")
        print(f"DNS fapi.binance.com -> {ip}")
    except Exception as e:
        print(f"DNS 失败: {e}")

    proxy = "http://127.0.0.1:7890"
    for name, base in hosts:
        url = f"{base}/fapi/v1/time"
        try:
            r = requests.get(url, timeout=8)
            print(f"OK  {name} {r.status_code} {r.text[:80]}")
        except Exception as e:
            print(f"直连失败 {name}: {e}")
            try:
                r = requests.get(url, proxies={"http": proxy, "https": proxy}, timeout=8)
                print(f"OK  代理 {name} {r.status_code} {r.text[:80]}")
            except Exception as e2:
                print(f"代理失败 {name}: {e2}")


if __name__ == "__main__":
    test_connection()