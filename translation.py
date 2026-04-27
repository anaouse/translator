import time

import requests

# 复用同一个底层 TCP ？
youdao_session = requests.Session()


def youdao_translation(word: str) -> str:
    """查询单词释义（有道词典 suggest API）

    Args:
        word: 要查询的单词或短语

    Returns:
        格式化后的 "entry: explain" 字符串，每行一条结果；
        如果出错则返回以 "error:" 或 "network error:" 开头的错误信息。
    """
    start = time.time()

    url = "https://dict.youdao.com/suggest"
    params = {
        "num": 2,
        "ver": "3.0",
        "doctype": "json",
        "cache": "false",
        "le": "en",
        "q": word,
    }

    try:
        resp = youdao_session.get(url, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return f"network error: {e}"
    except ValueError as e:
        return f"json decode error: {e}"

    result = data.get("result", {})
    msg = result.get("msg", "")
    code = result.get("code", 0)

    if code != 200 or msg != "success":
        return f"error: {msg}"

    entries = data.get("data", {}).get("entries", [])
    if not entries:
        return "no results"

    lines = [f"{item['entry']}: {item['explain']}" for item in entries]

    print(f"[耗时] {time.time() - start:.3f}s")

    return "\n".join(lines)
