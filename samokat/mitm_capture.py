"""
Mitmproxy addon: сохраняет ВСЕ HTTP-запросы к *.samokat.ru в JSONL.
Запуск: mitmdump -s mitm_capture.py --listen-host 0.0.0.0 --listen-port 8080
"""
import json
import pathlib
from datetime import datetime
from mitmproxy import http

OUT = pathlib.Path(__file__).parent / "out" / "samokat_traffic.jsonl"
OUT.parent.mkdir(exist_ok=True)

_n = 0


def response(flow: http.HTTPFlow) -> None:
    global _n
    host = flow.request.pretty_host
    if "samokat.ru" not in host and "lavka.yandex" not in host:
        return
    _n += 1
    req_headers = dict(flow.request.headers)
    resp_headers = dict(flow.response.headers) if flow.response else {}
    req_body = flow.request.get_text(strict=False) or ""
    resp_body = flow.response.get_text(strict=False) if flow.response else ""
    rec = {
        "n": _n,
        "ts": datetime.now().isoformat(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "status": flow.response.status_code if flow.response else None,
        "req_headers": req_headers,
        "req_body": req_body[:20000],
        "resp_headers": resp_headers,
        "resp_body": resp_body[:200000],
    }
    with OUT.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    # Краткий лог
    print(f"[{_n:4d}] {flow.request.method} {flow.response.status_code if flow.response else '-'} "
          f"{flow.request.pretty_url[:140]}")
