"""
Локальный HTTP/HTTPS прокси-bridge.
Слушает локальный порт без auth, пересылает все запросы на upstream-прокси
(задаётся через env PROXY_HOST/PROXY_PORT) с добавлением заголовка Proxy-Authorization.

Нужно, потому что Chromium/Playwright не поддерживают proxy с auth для HTTPS-CONNECT.
"""
import asyncio
import base64
import os
import sys

LOCAL_HOST = os.environ.get("LOCAL_PROXY_HOST", "127.0.0.1")
LOCAL_PORT = int(os.environ.get("LOCAL_PROXY_PORT", "8899"))
# Upstream residential/mobile proxy. Configure via environment:
#   PROXY_HOST, PROXY_PORT         — upstream host:port
#   PROXY_USER, PROXY_PASS         — upstream credentials (Basic auth)
UPSTREAM_HOST = os.environ.get("PROXY_HOST", "proxy.example.com")
UPSTREAM_PORT = int(os.environ.get("PROXY_PORT", "0"))
AUTH = f"{os.environ.get('PROXY_USER', '')}:{os.environ.get('PROXY_PASS', '')}"
AUTH_B64 = base64.b64encode(AUTH.encode()).decode()


async def pipe(src: asyncio.StreamReader, dst: asyncio.StreamWriter):
    try:
        while True:
            data = await src.read(65536)
            if not data:
                break
            dst.write(data)
            await dst.drain()
    except Exception:
        pass
    try:
        dst.close()
    except Exception:
        pass


async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer = writer.get_extra_info("peername")
    # Читаем первый запрос клиента (до \r\n\r\n).
    head = b""
    try:
        while b"\r\n\r\n" not in head:
            chunk = await asyncio.wait_for(reader.read(4096), timeout=15)
            if not chunk:
                break
            head += chunk
    except asyncio.TimeoutError:
        print(f"[{peer}] timeout reading head (got {len(head)} bytes: {head[:80]!r})", flush=True)
        writer.close(); return
    if not head:
        print(f"[{peer}] empty head", flush=True)
        writer.close(); return
    first_line = head.split(b"\r\n", 1)[0]
    print(f"[{peer}] -> {first_line!r}", flush=True)

    # Inject Proxy-Authorization (между первой строкой и \r\n\r\n)
    auth_header = f"\r\nProxy-Authorization: Basic {AUTH_B64}".encode()
    # Удалим предыдущую, если вдруг есть
    lines = head.split(b"\r\n")
    lines = [ln for ln in lines if not ln.lower().startswith(b"proxy-authorization:")]
    head = b"\r\n".join(lines)
    # Добавим перед \r\n\r\n
    head = head.replace(b"\r\n\r\n", auth_header + b"\r\n\r\n", 1)

    # Подключаемся к upstream
    try:
        up_r, up_w = await asyncio.open_connection(UPSTREAM_HOST, UPSTREAM_PORT)
    except Exception as e:
        print("upstream err:", e, file=sys.stderr)
        writer.close(); return

    up_w.write(head)
    await up_w.drain()

    # Прочитаем первый ответ от upstream и залогируем
    try:
        first = await asyncio.wait_for(up_r.read(4096), timeout=10)
        print(f"[{peer}] <- upstream first bytes: {first[:120]!r}", flush=True)
        writer.write(first)
        await writer.drain()
    except asyncio.TimeoutError:
        print(f"[{peer}] upstream timeout (no response)", flush=True)
        writer.close(); up_w.close(); return

    # Полнодуплексная пересылка
    await asyncio.gather(pipe(reader, up_w), pipe(up_r, writer))


async def main():
    srv = await asyncio.start_server(handle, LOCAL_HOST, LOCAL_PORT)
    print(f"local proxy on {LOCAL_HOST}:{LOCAL_PORT}, upstream={UPSTREAM_HOST}:{UPSTREAM_PORT}",
          flush=True)
    async with srv:
        await srv.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
