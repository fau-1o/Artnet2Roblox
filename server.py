"""
DMX Multi-Universe Bridge - Server (release)

Alur: artnet2WSS.py --(WebSocket)--> server ini --(HTTP /polling)--> script Roblox (Lua)

Jalankan saja:   python Server_multi_universe_polling.py
Default aman: hanya menerima koneksi dari PC ini (127.0.0.1).
Kalau Art-Net client ada di PC lain di LAN:  python Server_multi_universe_polling.py --lan
Butuh:  pip install aiohttp
"""
import argparse
import asyncio
import json
import time
from collections import deque
from datetime import datetime, timezone

from aiohttp import web

# ------------------------------------------------------------------
# Konstanta (default sudah optimal, tidak perlu diubah)
# ------------------------------------------------------------------
DEFAULT_PORT = 5311
MAX_UNIVERSES = 8            # harus sama dengan Lua & artnet2WSS.py
MAX_USERS = 16               # batas user aktif (cegah memori membengkak)
MAX_USERNAME_LEN = 64
POLLING_FRAMES = 60          # frame maks yang ditahan per universe di antara dua polling
KEEPALIVE_INTERVAL = 1.0     # state yang tidak berubah dikirim ulang tiap sekian detik
USER_IDLE_TIMEOUT = 60.0     # buang universe yang tidak ada data selama sekian detik
MAX_WS_MESSAGE = 256 * 1024  # 8 universe penuh masih < 40 KB

# Kunci = (username, universe). Tiap universe berdiri sendiri.
universe_buffers: dict[tuple[str, int], deque] = {}
universe_states: dict[tuple[str, int], dict[str, int]] = {}  # hanya channel > 0
last_seen: dict[tuple[str, int], float] = {}
last_frame: dict[tuple[str, int], float] = {}


def log(message: str) -> None:
    print(time.strftime("%H:%M:%S"), message, flush=True)


def compact_json(obj) -> str:
    return json.dumps(obj, separators=(",", ":"))


def normalize_payload(payload) -> list[tuple[str, int, dict[str, int]]]:
    """Validasi paket dari client. Channel bernilai 0 tidak disimpan (dianggap 0)."""
    if not isinstance(payload, dict):
        return []
    username = payload.get("Username") or payload.get("username") or payload.get("name")
    if not isinstance(username, str):
        return []
    username = username.strip()[:MAX_USERNAME_LEN]
    if not username:
        return []

    universes = payload.get("universes")
    if isinstance(universes, dict):
        items = list(universes.items())
    else:  # format lama: satu universe
        items = [(payload.get("universe", payload.get("Universe", 1)),
                  payload.get("data", payload.get("dmx", payload.get("channels"))))]

    result = []
    for raw_universe, raw_data in items:
        try:
            universe = int(raw_universe)
        except (TypeError, ValueError, OverflowError):
            continue
        if not 1 <= universe <= MAX_UNIVERSES or not isinstance(raw_data, dict):
            continue
        channels: dict[str, int] = {}
        for raw_channel, raw_value in raw_data.items():
            try:
                ch = int(raw_channel)
                value = int(raw_value)
            except (TypeError, ValueError, OverflowError):
                continue
            if 1 <= ch <= 512 and value > 0:
                channels[str(ch)] = min(255, value)
        result.append((username, universe, channels))
    return result


def ingest(items) -> None:
    now = time.time()
    for username, universe, channels in items:
        key = (username, universe)
        if key not in universe_states:
            active_users = {u for u, _ in universe_states}
            if username not in active_users and len(active_users) >= MAX_USERS:
                continue  # terlalu banyak user, abaikan yang baru
        last_seen[key] = now
        if universe_states.get(key) == channels:
            continue  # tidak berubah: tidak perlu frame baru (keepalive akan mengulang)
        universe_states[key] = channels
        last_frame[key] = now
        q = universe_buffers.setdefault(key, deque(maxlen=POLLING_FRAMES))
        q.append({"timestamp": now, "channels": channels})


async def safe_send(ws: web.WebSocketResponse, data) -> None:
    try:
        await ws.send_str(compact_json(data))
    except Exception:
        pass


async def websocket_handler(request: web.Request) -> web.StreamResponse:
    # compress=False: tanpa kompresi supaya latensi minimum di jaringan lokal
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=MAX_WS_MESSAGE, compress=False)
    if not ws.can_prepare(request).ok:
        return web.json_response({
            "message": "DMX multi-universe bridge ready",
            "websocket": "/ws",
            "http": {"polling": "/polling", "state": "/state"},
            "max_universes": MAX_UNIVERSES,
        })
    await ws.prepare(request)
    log(f"Client terhubung: {request.remote}")
    await safe_send(ws, {"type": "hello", "message": "DMX multi-universe bridge ready"})
    try:
        async for message in ws:
            if message.type != web.WSMsgType.TEXT:
                continue
            try:
                payload = json.loads(message.data)
            except json.JSONDecodeError:
                await safe_send(ws, {"type": "error", "message": "Invalid JSON"})
                continue
            items = normalize_payload(payload)
            if not items:
                await safe_send(ws, {"type": "error",
                                     "message": f"Expected Username and universes 1..{MAX_UNIVERSES}"})
                continue
            ingest(items)
    finally:
        log(f"Client terputus: {request.remote}")
    return ws


async def get_polling_data(_request: web.Request) -> web.Response:
    """Ambil semua frame baru lalu kosongkan antrean (satu poller saja)."""
    response_data: dict[str, dict[str, dict]] = {}
    for (username, universe), q in list(universe_buffers.items()):
        if not q:
            continue
        frames = list(q)
        q.clear()
        response_data.setdefault(username, {})[str(universe)] = {
            f"t{i + 1}": frame for i, frame in enumerate(frames)
        }
    return web.json_response(
        {"generatedAt": datetime.now(timezone.utc).isoformat(), "data": response_data},
        headers={"Cache-Control": "no-store"},
        dumps=compact_json,
    )


async def get_state(_request: web.Request) -> web.Response:
    data: dict[str, dict[str, dict]] = {}
    for (username, universe), channels in universe_states.items():
        data.setdefault(username, {})[str(universe)] = channels
    return web.json_response(
        {"generatedAt": datetime.now(timezone.utc).isoformat(), "data": data},
        headers={"Cache-Control": "no-store"},
        dumps=compact_json,
    )


async def maintenance_loop() -> None:
    """Keepalive state yang diam + buang universe yang sudah tidak aktif."""
    while True:
        await asyncio.sleep(0.25)
        now = time.time()
        for key, channels in list(universe_states.items()):
            seen = last_seen.get(key, 0.0)
            if now - seen > USER_IDLE_TIMEOUT:
                for table in (universe_states, universe_buffers, last_seen, last_frame):
                    table.pop(key, None)
                continue
            if now - last_frame.get(key, 0.0) >= KEEPALIVE_INTERVAL:
                last_frame[key] = now
                q = universe_buffers.setdefault(key, deque(maxlen=POLLING_FRAMES))
                q.append({"timestamp": now, "channels": channels})


async def main(host: str, port: int) -> None:
    app = web.Application()
    app.router.add_get("/", websocket_handler)
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/polling", get_polling_data)
    app.router.add_get("/state", get_state)
    runner = web.AppRunner(app)
    await runner.setup()
    try:
        await web.TCPSite(runner, host, port, reuse_address=True).start()
    except OSError as exc:
        log(f"GAGAL membuka {host}:{port} -> {exc}")
        log("Port sedang dipakai? Tutup server lama atau jalankan dengan --port <angka lain>.")
        await runner.cleanup()
        return
    task = asyncio.create_task(maintenance_loop())
    scope = "semua perangkat di LAN" if host == "0.0.0.0" else "hanya PC ini"
    log(f"DMX Multi-Universe Server READY | port {port} | universe 1-{MAX_UNIVERSES} | akses: {scope}")
    log("Tekan Ctrl+C untuk berhenti.")
    try:
        await asyncio.Event().wait()
    finally:
        task.cancel()
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DMX Multi-Universe Bridge Server")
    parser.add_argument("--lan", action="store_true",
                        help="izinkan koneksi dari PC lain di LAN (default: hanya 127.0.0.1)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = parser.parse_args()
    try:
        asyncio.run(main("0.0.0.0" if args.lan else "127.0.0.1", args.port))
    except KeyboardInterrupt:
        log("Server dihentikan.")
