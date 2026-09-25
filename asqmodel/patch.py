import re

f = r"J:\l2data\asq\features.py"
with open(f, "r", encoding="utf-8") as fp:
    content = fp.read()

new_func = '''def get_market_speed(data, price_int):
    deltalist = np.linspace(price_int, price_int * 10, 10)
    lambdas = []
    for delta in deltalist:
        ask_hit = data[("ap", "max")].shift(-1) > (data[("ap", "last")] + delta)
        bid_hit = data[("bp", "min")].shift(-1) < (data[("bp", "last")] - delta)
        n_hit = (ask_hit | bid_hit).sum()
        lambdas.append(n_hit / len(data))
    lambdas = np.array(lambdas)
    valid = lambdas > 0
    if valid.sum() < 2:
        return 1.0, 0.1
    x = deltalist[valid]
    y = lambdas[valid]
    k, log_A = np.polyfit(x, np.log(y), 1)
    k = -k
    A = np.exp(log_A)
    if k <= 0 or not np.isfinite(A) or not np.isfinite(k):
        return 1.0, 0.1
    return float(A), float(k)'''

pattern = r"def get_market_speed\(data, price_int\):.*?(?=\n\n\ndef |\n\n\n# |\Z)"
content_new = re.sub(pattern, new_func, content, count=1, flags=re.DOTALL)

with open(f, "w", encoding="utf-8") as fp:
    fp.write(content_new)

print("替换完成")
